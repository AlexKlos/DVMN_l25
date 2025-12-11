from django import forms
from django.db.models import Prefetch, Case, When, Value, IntegerField
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views


from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem, OrderItems
from locations.geodata import fetch_coordinates, distance_km
from locations.models import Location


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, 'login.html', context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect('restaurateur:RestaurantView')
                return redirect('start_page')

        return render(request, 'login.html', context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name='products_list.html', context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name='restaurants_list.html', context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects
        .not_finished()
        .with_total_cost()
        .select_related('cooking_restaurant')
        .annotate(
            status_priority=Case(
                When(status=Order.STATUS_NEW, then=1),
                When(status=Order.STATUS_ASSEMBLING, then=2),
                When(status=Order.STATUS_DELIVERING, then=3),
                default=4,
                output_field=IntegerField(),
            )
        )
        .order_by('status_priority', 'registered_at')
        .prefetch_related(
            Prefetch(
                'items',
                queryset=OrderItems.objects.select_related('product'),
            )
        )
    )

    restaurants = list(
        Restaurant.objects.prefetch_related(
            Prefetch(
                'menu_items',
                queryset=RestaurantMenuItem.objects
                .filter(availability=True)
                .select_related('product'),
                to_attr='available_menu_items',
            )
        )
    )

    order_addresses = {order.address for order in orders if order.address}
    restaurant_addresses = {restaurant.address for restaurant in restaurants if restaurant.address}
    all_addresses = order_addresses | restaurant_addresses

    locations = Location.objects.filter(address__in=all_addresses)
    coords_by_address = {}
    for location in locations:
        if location.lon is None or location.lat is None:
            continue
        coords_by_address[location.address] = (location.lon, location.lat)

    def get_or_fetch_coords(address: str) -> tuple | None:
        if not address:
            return None
        coords = coords_by_address.get(address)
        if coords is not None:
            return coords
        coords = fetch_coordinates(address)
        if coords is None:
            return None
        lon, lat = coords
        Location.objects.update_or_create(
            address=address,
            defaults={'lon': lon, 'lat': lat},
        )
        coords_by_address[address] = coords
        return coords

    for order in orders:
        order_coords = get_or_fetch_coords(order.address)

        if order_coords is None:
            order.available_restaurants = []
            order.geocoder_error = True
            continue

        order_product_ids = {item.product_id for item in order.items.all()}

        candidates = []

        for restaurant in restaurants:
            rest_product_ids = {
                item.product_id for item in restaurant.available_menu_items
            }

            if not order_product_ids.issubset(rest_product_ids):
                continue

            rest_coords = get_or_fetch_coords(restaurant.address)
            if rest_coords is None:
                continue

            dist = distance_km(order_coords, rest_coords)
            candidates.append((restaurant, dist))

        candidates.sort(key=lambda pair: pair[1])

        order.available_restaurants = candidates
        order.geocoder_error = False if candidates else True

    return render(request, 'order_items.html', context={
        'orders': orders,
    })
