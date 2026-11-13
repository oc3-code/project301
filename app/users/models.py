from django.db import models

# Create your models here.
class UserType(models.Model):
    code = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=128)

    class Meta:
        db_table = "user_types"

    def __str__(self):
        return self.code