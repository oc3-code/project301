from django.urls import path
from . import views

urlpatterns = [
    path("product/", views.ProductListCreate.as_view(),name="product-list"),
    path("product/<int:pk>", views.ProductDetail.as_view(), name="product-detail"),
    path("", views.OrderListCreate.as_view(),name="order-list"),
    path("<int:pk>", views.OrderDetail.as_view(), name="order-detail"),
]