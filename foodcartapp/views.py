import phonenumbers

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

    def get_checked_field(order_data, field_name, field_type=str):
        value = order_data.get(field_name)
        if value is None:
            raise ValueError(f'{field_name}: Required field')
        elif not isinstance(value, field_type):
            raise ValueError(f'{field_name}: Must be {field_type.__name__}')
        elif value in ([], ''):
            raise ValueError(f'{field_name}: Cannot be empty')

        return value
    
    def validate_phonenumber(value):
        try:
            number = phonenumbers.parse(value, 'RU')
            if not phonenumbers.is_valid_number(number):
                raise ValueError('phonenumber: Invalid format')
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            raise ValueError('phonenumber: Invalid phonenumber')
    
    order_data = request.data

    try:
        firstname = get_checked_field(order_data, 'firstname')
        lastname = get_checked_field(order_data, 'lastname')
        phonenumber = get_checked_field(order_data, 'phonenumber')
        phonenumber = validate_phonenumber(phonenumber)
        address = get_checked_field(order_data, 'address')
        products = get_checked_field(order_data, 'products', list)
        for item in products:
            product = get_checked_field(item, 'product', int)
            quantiti = get_checked_field(item, 'quantity', int)
            if quantiti <= 0:
                raise ValueError('quantity: Must be > 0')
            if not Product.objects.filter(id=product).exists():
                raise ValueError(f'product: Product with id={product} does not exist')
            
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    order = Order.objects.create(
        firstname=firstname,
        lastname=lastname,
        phonenumber=phonenumber,
        address=address,
    )

    for item in products:
        product = Product.objects.get(id=item['product'])
        OrderItems.objects.create(
            order=order,
            product=product,
            quantity=item['quantity'],
        )

    return Response({'order_id': order.id})
