from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^orders/settlement/$', views.OrderView.as_view()),
    re_path(r'^orders/$', views.SaveOrderView.as_view()),
]


