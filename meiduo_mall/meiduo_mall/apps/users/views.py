from django.shortcuts import render

# Create your views here.
# 判断账号是否存在
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from users.models import User
from . import serializers, contains
from .serializers import CreateUserSerializer, UserDetailSerializer, EmailUpdateSerializer, \
    AddressTitleSerializer, UserAddressSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView


# 注册逻辑实现
class UserRegisterView(CreateAPIView):
    # 校验参数   获取的参数： username, mobile ,password, password2, sms_code, allow
    # 保存数据
    # 返回
    # 使用序列化器实现
    serializer_class = CreateUserSerializer


# 判断账号是否存在
class UsernameCountView(APIView):
    def get(self, request, username):
        # 从数据库查询用户输入的用户名个数
        count = User.objects.filter(username=username).count()

        data = {
            "username": username,
            "count": count
        }

        return Response(data)


# 判断手机号是否存在
class MobileCountView(APIView):

    def get(self, request, mobile):
        # 从数据库查询用户输入的用户名个数
        count = User.objects.filter(mobile=mobile).count()

        data = {
            "mobile": mobile,
            "count": count
        }

        return Response(data)


# 获取用户个人中心信息
class UserDetailView(RetrieveAPIView):

    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# PUT /email/
# 保存email到数据库
class EmailView(UpdateAPIView):

    serializer_class = EmailUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# GET /emails/verification/?token=xxx
# 验证邮箱链接
class EmailVerifyView(APIView):
    def get(self, request):
        # 获取参数
        token = request.query_params.get('token')
        # 校验参数
        if not token:
            return Response({"message": 'token无效'}, status=status.HTTP_400_BAD_REQUEST)
        # 验证token
        user = User.check_user_token(token)
        # 如果得到的user无数据，说明链接无效
        if user is None:
            return Response({"message": '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 如果token有效，则修改数据库邮箱状态为已验证
            user.email_active = True
            user.save()
            # 返回
            return Response({"message": 'OK!'})


# 地址需要6个接口 增删改查， 默认地址， 默认标题
"""
新增 put /addresses/   create
修改 put /addresses/<pk> 修改某一地址   update 修改利用继承的UpdateModelMixin实现，只需指明查询集即可
查询 get /addresses/  list
删除 delete /addresses/<pk>  destroy

默认地址 put /addresses/<pk>/status  status
修改默认标题 put /addresses/<pk>/title  title 
"""


class AddressViewSet(CreateModelMixin, UpdateModelMixin, GenericViewSet):

    serializer_class = UserAddressSerializer
    permission_classes = [IsAuthenticated]

    # 重写get_queryset方法，使返回视图的查询集变为修改使用
    def get_queryset(self):
        # 返回没有逻辑删除的对象
        return self.request.user.addresses.filter(is_deleted=False)

    # 查询 get /addresses/  list
    # 自己指定list方法，查询的数据需要默认地址和默认标题
    # 'user_id': user.id,
    # 'default_address_id': user.default_address_id,
    # 'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
    # 'addresses
    def list(self, request, *args, **kwargs):
        # 获取查询视图集
        queryset = self.get_queryset()
        # 获取序列化器的addresses数据并序列化
        serializer = self.get_serializer(queryset, many=True)
        # 获取请求的对象
        user = self.request.user
        # 返回查询的数据
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': contains.ADDRESS_COUNT_LIMIT,
            'addresses': serializer.data,
        })

    # 重写create方法，新增地址的最大个数不能大于20个
    # 新增 post / addresses / create
    def create(self, request, *args, **kwargs):
        # 获取地址薄的个数
        count = request.user.addresses.count()
        # 如果大于20，则返回提示
        if count > contains.ADDRESS_COUNT_LIMIT:
            return Response({"message": "地址博数量已达上限"}, status=status.HTTP_400_BAD_REQUEST)
        # 调用父类的保存方法，新增数据
        return super().create(request, *args, **kwargs)

    # 删除 delete /addresses/<pk>  destroy
    def destroy(self, request, *args, **kwargs):
        # 获取删除的对象
        addresses = self.get_object()
        # 进行逻辑删除
        addresses.is_delete = True
        addresses.save()

        # 删除成功返回204
        return Response(status=status.HTTP_204_NO_CONTENT)

    # 默认地址 put / addresses / < pk > / status
    @action(methods=['PUT'], detail=True)  # 设置单一数据，detail为True
    def status(self, request, pk=None):
        # 获取设置默认地址的对象
        address = self.get_object()
        # 将获取的对象地址设为用户的默认地址
        request.user.default_address = address
        request.user.save()

        return Response({"message": "OK"})

    # 修改默认标题 put /addresses/ <pk> / title
    @action(methods=['PUT'], detail=True)
    def title(self, request, pk=None):  # 类似于update方法
        # 修改默认标题需要用户输入，前端回传入默认标题数据，需要用到序列化器
        # 获取设置默认地址的对象
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)   # data为前端传入的默认标题
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 把保存后的数据返回
        return Response(serializer.data)
