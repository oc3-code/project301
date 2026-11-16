from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import UserType, User, Product, Order, OrderProduct

class UserTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserType
        fields = ['id','code','description']

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id','name','login','password','user_type']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = "__all__"

class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = "__all__"  

class OrderProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderProduct
        fields = "__all__" 