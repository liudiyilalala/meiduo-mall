from django.shortcuts import render

# Create your views here.
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from goods.models import SKU
from goods.serializers import SKUSerializer, SKUIndexSerializer
from drf_haystack.viewsets import HaystackViewSet


class SKUListView(ListAPIView):
    # 将返回的数据进行序列化
    serializer_class = SKUSerializer
    # 排序
    """REST framework提供了对于排序的支持，使用REST framework提供的OrderingFilter过滤器后端即可。
    OrderingFilter过滤器要使用ordering_fields 属性来指明可以进行排序的字段有哪些。
    """
    filter_backends = [OrderingFilter]
    ordering_fields = ('create_time', 'price', 'sales')

    # 分页  # 自定义Pagination类，全局设置

    # 重写get_queryset查询结果集
    def get_queryset(self):
        # 从路由中获取商品类别
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)


class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]

    serializer_class = SKUIndexSerializer


