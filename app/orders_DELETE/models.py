from django.db import models
from django.utils import timezone

from users.models import User

# Create your models here.
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