from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import UserType, User

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



