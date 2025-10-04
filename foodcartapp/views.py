import json

from django.http import JsonResponse
from django.templatetags.static import static
from rest_framework.decorators import api_view
from rest_framework.response import Response


from .models import Product, Order, OrderItems


@api_view(['GET'])
def banners_list_api(request):
    banners = [
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ]
    return Response(banners)


@api_view(['GET'])
def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)

    return Response(dumped_products)


@api_view(['POST'])
def register_order(request):
    order_data = request.data
    
    order = Order.objects.create(
        firstname=order_data['firstname'],
        lastname=order_data['lastname'],
        phonenumber=order_data['phonenumber'],
        address=order_data['address'],
    )

    for item in order_data['products']:
        product = Product.objects.get(id=item['product'])
        OrderItems.objects.create(
            order=order,
            product=product,
            quantity=item['quantity'],
        )

    return Response({'order_id': order.id})
