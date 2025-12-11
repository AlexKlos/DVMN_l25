from django.db import models
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField

from django.db.models import F, Sum, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Coalesce
from django.utils import timezone


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class OrderQuerySet(models.QuerySet):
    def with_total_cost(self):
        line_total = ExpressionWrapper(
            F('items__quantity') * F('items__price'),
            output_field=DecimalField(max_digits=8, decimal_places=2),
        )
        return self.annotate(
            total_cost=Coalesce(
                Sum(line_total),
                Value(0),
                output_field=DecimalField(max_digits=8, decimal_places=2),
            )
        )
    
    def not_finished(self):
        return self.exclude(status=Order.STATUS_FINISHED)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f'{self.restaurant.name} - {self.product.name}'


class Order(models.Model):
    STATUS_NEW = 'NEW'
    STATUS_ASSEMBLING = 'ASSEMBLING'
    STATUS_DELIVERING = 'DELIVERING'
    STATUS_FINISHED = 'FINISHED'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_ASSEMBLING, 'Сборка'),
        (STATUS_DELIVERING, 'Доставка'),
        (STATUS_FINISHED, 'Завершён'),
    ]
    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_NON_CASH = 'non-cash'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CASH, 'наличные'),
        (PAYMENT_METHOD_NON_CASH, 'безнал'),
    ]

    firstname = models.CharField('имя', max_length=50)
    lastname = models.CharField('фамилия', max_length=50)
    phonenumber = PhoneNumberField('телефон', db_index=True)
    address = models.CharField('адрес', max_length=200)
    objects = OrderQuerySet.as_manager()
    comment = models.CharField('комментарий', max_length=200, blank=True)
    registered_at = models.DateTimeField('создан', default=timezone.now, db_index=True)
    called_at = models.DateTimeField('время звонка', null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField('доставлен', null=True, blank=True, db_index=True)
    status = models.CharField(
        'статус', 
        max_length=12, 
        choices=STATUS_CHOICES, 
        default=STATUS_NEW, 
        db_index=True
    )
    payment_method = models.CharField(
        'способ оплаты', 
        max_length=10, 
        choices=PAYMENT_METHOD_CHOICES, 
        db_index=True
    )
    cooking_restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='ресторан',
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
    
    def __str__(self):
        return f'Заказ {self.pk} - {self.firstname} {self.lastname}'


class OrderItems(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        verbose_name='заказ',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        'Product',
        related_name='order_items',
        verbose_name='товар',
        on_delete=models.CASCADE,
    )
    quantity = models.PositiveIntegerField(
        'количество',
        validators=[MinValueValidator(1)],
        default=1,
    )
    price = models.DecimalField(
        verbose_name='цена в момент заказа',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'позиция заказа'
        verbose_name_plural = 'позиции заказа'
        unique_together = [
            ['order', 'product']
        ]

    def __str__(self):
        return f'{self.product.name} x {self.quantity} (заказ {self.order_id})'
