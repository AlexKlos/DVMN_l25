from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Order, OrderItems, Product
from django.db import IntegrityError, transaction


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItems
        fields = ['product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    firstname = serializers.CharField(max_length=50)
    lastname = serializers.CharField(max_length=50)
    phonenumber = PhoneNumberField(region='RU')
    address = serializers.CharField(max_length=200)
    products = OrderItemSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'products']

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        try:
            with transaction.atomic():
                order = Order.objects.create(**validated_data)
    
                items = []
                for item in products_data:
                    product = item['product']
                    quantity = item['quantity']
                    items.append(OrderItems(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.price,
                    ))
                OrderItems.objects.bulk_create(items)

                # raise RuntimeError('test rolllback')
    
                return order
        except IntegrityError as e:
            raise serializers.ValidationError({'non_field_errors': [str(e)]})
