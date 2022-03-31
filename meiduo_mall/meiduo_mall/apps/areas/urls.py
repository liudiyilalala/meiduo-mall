from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
]

router = DefaultRouter()
router.register(r'areas', views.AreasViewSet, basename='areas')
urlpatterns += router.urls

