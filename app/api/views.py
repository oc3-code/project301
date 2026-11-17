from django.shortcuts import render
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import UserType, User, Product, Order, OrderProduct, Shipment
from .serializers import (UserTypeSerializer, UserSerializer, ProductSerializer, 
                          OrderSerializer, OrderProductSerializer, ShipmentSerializer)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.db import DatabaseError

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

class ProductListCreate(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class OrderListCreate(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer  

class OrderProductListCreate(generics.ListCreateAPIView):
    queryset = OrderProduct.objects.all()
    serializer_class = OrderProductSerializer

@require_GET
def order_items(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    items = order.items.select_related("product")
    return JsonResponse(OrderProductSerializer(items, many=True).data, safe=False)

class OrderProductDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderProduct.objects.all()
    serializer_class = OrderProductSerializer 

# /orderproduct/order/<order_id>/product/<product_id>  DELETE, PATCH, PUT
@api_view(["DELETE", "PATCH", "PUT"])
def order_product_detail(request, order_id, product_id):
    op = get_object_or_404(OrderProduct, order_id=order_id, product_id=product_id)
    if request.method == "DELETE":
        op.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    if not {"quantity", "sale_price"} & set(request.data):
        return Response(status=status.HTTP_400_BAD_REQUEST)
    ser = OrderProductSerializer(op, data={k: request.data[k] for k in ("quantity", "sale_price") if k in request.data}, partial=True)
    ser.is_valid(raise_exception=True)  # returns 400 with field errors
    ser.save()
    return Response(ser.data)

class ShipmentListCreate(generics.ListCreateAPIView):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer

class ShipmentDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer  