from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^cart/$', views.CartView.as_view()),
    # re_path(r'^cart/selection/$', views.CartSelectAllView.as_view()),
]


