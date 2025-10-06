from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Order, OrderItems, Product

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
    products = OrderItemSerializer(many=True, allow_empty=False)

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        order = Order.objects.create(**validated_data)
        for item in products_data:
            OrderItems.objects.create(order=order, **item)
        return order
    