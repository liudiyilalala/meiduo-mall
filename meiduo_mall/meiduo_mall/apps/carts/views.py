import base64
import pickle

from django.shortcuts import render

# Create your views here.
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from carts import constants
from .serializers import AddCartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer
from goods.models import SKU


class CartView(GenericAPIView):
    """购物车视图"""

    serializer_class = AddCartSerializer

    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        """
        pass

    def post(self, request):
        # 获取参数
        # 校验参数
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 取出校验后的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            user = None
        # 如果用户登录，将购物车数据保存到redis
        if user and user.is_authenticated:
            # 建立redis链接
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            # 保存user_id, sku_id, count到哈希类型的redis中
            # carts_user_id: {sku_id1: count, sku_id3: count, sku_id5: count, ...}
            pl.hincrby("carts_userid_%s" % user.id, sku_id, count)
            # 如果selected有值，保存selected到集合类型的redis
            # selected_user_id: [sku_id1, sku_id3, ...]
            if selected:
                pl.sadd("selected_userid_%s" % user.id, sku_id)

            pl.execute()
            # 返回序列化后的数据
            return Response(serializer.data)
        # 如果没有登录，将购物车数据保存到cookie中
        else:
            # 从cookie中获取购物车数据
            # cart:{
            #     "sku_id":{
            #         "count":"1",
            #         "selected":"True"
            #     },
            cart_str = request.COOKIES.get('cart')
            # 将数据通过base64和pickle解码
            if cart_str:
                cart_str = cart_str.encode()  # str >> byte
                cart_byte = base64.b64decode(cart_str)   # 将base64编码后的bytes类型数据进行解码，返回解码后的bytes类型数
                cart_dict = pickle.loads(cart_byte)  # byte >> python数据
            else:
                cart_dict = {}
            # 保存数据到cookie中
            # 如果商品在cookie中，将商品数量累加，设置selected
            if sku_id in cart_dict:
                cart_dict[sku_id]['count'] += count
                cart_dict[sku_id]['selected'] = selected
            else:
                # 商品不在cookie中，直接设置
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }

            # 将保存后的数据编码
            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 设置cookie并返回
            response = Response(serializer.data)
            response.set_cookie('cart', cart_cookie, max_age=constants.SET_COOKIE_MAX_AGE)

            return response

    # 获取购物车数据
    def get(self, request):
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            user = None
        # 如果登录从redis查询
        if user and user.is_authenticated:
            # 建立redis链接
            redis_conn = get_redis_connection('cart')
            # 查询哈希类型的redis中的sku_id, count，返回值为byte类型
            # carts_user_id: {sku_id1: count, sku_id3: count, sku_id5: count, ...}
            redis_cart = redis_conn.hgetall("carts_userid_%s" % user.id)
            # 查询集合类型的redis中的selected
            redis_cart_selected = redis_conn.smembers("selected_userid_%s" % user.id)
            # 遍历redis_cart，将sku_id和count由键值对变为单个对象
            # sku_id : count >> (sku_id, count)
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_cart_selected
                }
        # 如果未登录从cookie获取
        else:
            cookie_cart = request.COOKIES.get('cart')
            if cookie_cart:
                # 将查询到的数据解码
                cart_dict = pickle.loads(base64.b64decode(cookie_cart.encode()))
            else:
                # 表示cookie中没有购物车数据
                cart_dict = {}

        # 通过数据库查询数据
        # 获取sku_id列表
        sku_id_list = cart_dict.keys()
        # 通过sku_id获取全部sku的数据
        sku_obj_list = SKU.objects.filter(id__in=sku_id_list)
        # 遍历sku_obj_list，取出单个sku数据
        for sku in sku_obj_list:
            # 向sku对象添加count，selected属性，用于前端展示
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']
        # 序列化返回
        serializer = CartSKUSerializer(sku_obj_list, many=True)
        return Response(serializer.data)

    # 修改购物车
    def put(self, request):

        # 获取当前的序列化器对象，对传入的参数进行反序列化
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 取出校验后的数据
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            user = None
        # 用户登录修改redis数据库内数据
        if user and user.is_authenticated:
            # 建立redis链接
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            # 修改user_id, sku_id, count到哈希类型的redis
            # carts_user_id: {sku_id1: count, sku_id3: count, sku_id5: count, ...}
            pl.hset("carts_userid_%s" % user.id, sku_id, count)
            # 如果selected有值，保存selected到集合类型的redis
            # selected_user_id: [sku_id1, sku_id3, ...]
            if selected:
                pl.sadd("selected_userid_%s" % user.id, sku_id)
            else:
                # 如果没有值，表示取消勾选，则删除掉selected内的值
                pl.srem("selected_userid_%s" % user.id, sku_id)

            pl.execute()
            return Response(serializer.data)
        # 用户未登录修改cookie数据
        else:
            cart_str = request.COOKIES.get('cart')
            # 将数据通过base64和pickle解码
            if cart_str:
                cart_str = cart_str.encode()  # str >> byte
                cart_byte = base64.b64decode(cart_str)  # 将base64编码后的bytes类型数据进行解码，返回解码后的bytes类型数
                cart_dict = pickle.loads(cart_byte)  # byte >> python数据
            else:
                cart_dict = {}

            response = Response(serializer.data)

            # 修改cookie中数据
            """如果商品不在cookie中，则直接返回序列化的数据
            幂等性： 不论请求了几次，数据都是一样。如count修改为了2个，用户在修改后请求多次，count仍为2
            """
            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }

                # 将修改后的数据编码
                cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

                # 设置cookie并返回

                response.set_cookie('cart', cart_cookie, max_age=constants.SET_COOKIE_MAX_AGE)
            return response

    # 删除购物车
    def delete(self, request):
        # 传入参数反序列化校验
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 取出校验后的数据
        sku_id = serializer.validated_data['sku_id']
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            user = None
        # 如果登录删除redis数据
        if user and user.is_authenticated:
            # 建立redis链接
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            # 删除哈希类型的redis
            # carts_user_id: {sku_id1: count, sku_id3: count, sku_id5: count, ...}
            pl.hdel("carts_userid_%s" % user.id, sku_id)
            # 删除setredis中的selected
            pl.srem("selected_userid_%s" % user.id, sku_id)

            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        # 没有登录删除cookie数据
        cart_str = request.COOKIES.get('cart')
        # 将数据通过base64和pickle解码
        if cart_str:
            cart_str = cart_str.encode()  # str >> byte
            cart_byte = base64.b64decode(cart_str)  # 将base64编码后的bytes类型数据进行解码，返回解码后的bytes类型数
            cart_dict = pickle.loads(cart_byte)  # byte >> python数据
        else:
            cart_dict = {}

        response = Response(status=status.HTTP_204_NO_CONTENT)
        if sku_id in cart_dict:
            del cart_dict[sku_id]

            # 删除之后转码
            cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 设置cookie并返回
            response.set_cookie('cart', cart_cookie, max_age=constants.SET_COOKIE_MAX_AGE)

        return response


# 购物车全选实现
class CartSelectAllView(GenericAPIView):
    """购物车全选视图"""

    serializer_class = CartSelectAllSerializer

    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        """
        pass

    def put(self, request):
        # 传入参数反序列化校验
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 取出校验后的数据
        selected = serializer.validated_data['selected']
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            user = None
        # 如果用户登录，将购物车数据保存到redis
        if user and user.is_authenticated:
            # 建立redis链接
            redis_conn = get_redis_connection('cart')
            # pl = redis_conn.pipeline()
            # 取出哈希类型的redis中的sku_id
            # carts_user_id: {sku_id1: count, sku_id3: count, sku_id5: count, ...}
            redis_cart = redis_conn.hgetall("carts_userid_%s" % user.id)
            sku_id_list = redis_cart.keys()
            # 如果selected有值，将所有的sku_id保存到selected中
            # selected_user_id: [sku_id1, sku_id3, ...]
            if selected:
                redis_conn.sadd("selected_userid_%s" % user.id, *sku_id_list)
            else:
                # 如果没有值，则取消全选，将selected中的值全部删除
                redis_conn.srem("selected_userid_%s" % user.id, *sku_id_list)
            # 返回序列化后的数据
            return Response({'message': 'ok!'})
        # 如果没有登录，将购物车数据保存到cookie中
        else:
            # 从cookie中获取购物车数据
            # cart:{
            #     "sku_id":{
            #         "count":"1",
            #         "selected":"True"
            #     },
            cart_str = request.COOKIES.get('cart')
            # 将数据通过base64和pickle解码
            if cart_str:
                cart_str = cart_str.encode()  # str >> byte
                cart_byte = base64.b64decode(cart_str)  # 将base64编码后的bytes类型数据进行解码，返回解码后的bytes类型数
                cart_dict = pickle.loads(cart_byte)  # byte >> python数据
            else:
                cart_dict = {}
            # 如果为空返回
            response = Response({'message': 'ok!'})

            # 如果商品在cookie中，设置selected
            if cart_dict:
                for sku_id in cart_dict:
                    cart_dict[sku_id]['selected'] = selected

                # 将保存后的数据编码
                cart_cookie = base64.b64encode(pickle.dumps(cart_dict)).decode()
                # 设置cookie
                response.set_cookie('cart', cart_cookie, max_age=constants.SET_COOKIE_MAX_AGE)

            return response
