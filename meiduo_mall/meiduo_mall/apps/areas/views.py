from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from .models import Area
from . import serializers
# Create your views here.
# 使用视图集实现查询省和市区的功能
# 省需要用到查询多个资源，市，区根据pk查询单一资源，所以用到了ReadOnlyModelViewSet视图集，提供了list和retrieve方法


# GET /areas/(?P<pk>\d+)/
class AreasViewSet(CacheResponseMixin, ReadOnlyModelViewSet):

    # 关掉分页
    pagination_class = None

    # 由于action是两种方式，需要根据不同的方式，使用不同的queryset
    def get_queryset(self):
        # list查询多个资源返回parent=None的查询
        if self.action == 'list':
            return Area.objects.filter(parent=None)  # 只返回顶级数据
        # retrieve返回根据pk查询的单一资源
        else:
            return Area.objects.all()

    # 序列化器也需要根据方式不同而选择不同的
    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.AreaSerializer
        # retrieve返回根据pk查询的单一资源
        else:
            return serializers.SubAreaSerializer
