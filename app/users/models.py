from django.db import models

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