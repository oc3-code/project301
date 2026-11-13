from django.urls import path
from . import views

urlpatterns = [
    path("usertype/", views.UserTypeListCreate.as_view(),name="usertype-list"),
    path("usertype/<int:pk>", views.UserTypeDetail.as_view(), name="usertype-detail"),
]

