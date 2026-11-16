from django.db import models
from django.utils import timezone
from decimal import Decimal

# Create your models here.
class UserType(models.Model):
    code = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=128)

    class Meta:
        db_table = "user_types"

    def __str__(self):
        return self.code

class User(models.Model):
    name = models.CharField(max_length=128)
    login = models.CharField(max_length=128, unique=True)
    password = models.CharField(max_length=256)
    user_type = models.ForeignKey(
        UserType,
        on_delete=models.PROTECT,
        related_name="users",
    )

    class Meta:
        db_table = "users"


class Product(models.Model):
    sku = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=1024)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = "products"

class Order(models.Model):
    created = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    class Meta:
        db_table = "orders"

class OrderProduct(models.Model):
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.IntegerField()
    sale_price = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        db_table = "orders_products"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="uniq_order_product",
            ),
        ]
