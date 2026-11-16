from django.urls import path
from . import views

urlpatterns = [
    path("usertype/", views.UserTypeListCreate.as_view(),name="usertype-list"),
    path("usertype/<int:pk>", views.UserTypeDetail.as_view(), name="usertype-detail"),
    path("user/", views.UserListCreate.as_view(),name="user-list"),
    path("user/<int:pk>", views.UserDetail.as_view(), name="user-detail"),
    path("product/", views.ProductListCreate.as_view(),name="product-list"),
    path("product/<int:pk>", views.ProductDetail.as_view(), name="product-detail"),
    path("order/", views.OrderListCreate.as_view(),name="order-list"),
    path("order/<int:pk>", views.OrderDetail.as_view(), name="order-detail"),    
]