from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^categories/(?P<category_id>\d+)/skus/$', views.SKUListView.as_view()),
]

router = DefaultRouter()
router.register('skus/search', views.SKUSearchViewSet, basename='skus_search')

urlpatterns += router.urls
