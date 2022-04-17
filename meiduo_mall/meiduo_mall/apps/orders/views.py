from decimal import Decimal

from django.shortcuts import render

# Create your views here.
from django_redis import get_redis_connection
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from goods.models import SKU
from orders.serializers import OrderSettlementSerializer, SaveOrderSerializer


class OrderView(GenericAPIView):
    """
        订单页面视图
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 从redis中获取购物车sku_id
        redis_conn = get_redis_connection('cart')
        # 获取购物车商品id和数量
        redis_cart = redis_conn.hgetall('carts_userid_%s' % user.id)
        # 获取勾选状态的数据
        redis_selected = redis_conn.smembers("selected_userid_%s" % user.id)
        # 提取出勾选状态的购物车数据
        cart_dict = {}
        for sku_id in redis_selected:
            cart_dict[int(sku_id)] = int(redis_cart[sku_id])
        # 通过数据库查找出商品
        sku_id_list = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_id_list)
        for sku in skus:
            sku.count = cart_dict[sku.id]

        # 设置运费
        freight = Decimal('10.00')
        # 将数据序列化返回
        serializer = OrderSettlementSerializer({'freight': freight, 'skus': skus})
        return Response(serializer.data)


class SaveOrderView(CreateAPIView):
    """
        保存订单

    """
    permission_classes = [IsAuthenticated]
    serializer_class = SaveOrderSerializer