from django.shortcuts import render
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import UserType, User
from .serializers import UserTypeSerializer, UserSerializer

# Create your views here.

class UserTypeListCreate(generics.ListCreateAPIView):
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer

class UserTypeDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserType.objects.all()
    serializer_class = UserTypeSerializer

class UserListCreate(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer



