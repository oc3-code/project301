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
    path("orderproduct/", views.OrderProductListCreate.as_view(),name="order-product-list"),
    path("orderproduct/order/<int:order_id>", views.order_items, name="order-product-list-by-order"),
    path("orderproduct/<int:pk>", views.OrderProductDetail.as_view(), name="order-product-detail"),
    path("orderproduct/order/<int:order_id>/product/<int:product_id>",
     views.order_product_detail, name="order-product-detail-by-keys"),
    path("shipment/", views.ShipmentListCreate.as_view(),name="shipment-list"),
    path("shipment/<int:pk>", views.ShipmentDetail.as_view(), name="shipment-detail"), 
]