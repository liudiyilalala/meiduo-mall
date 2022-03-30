from django.shortcuts import render

# Create your views here.
# 判断账号是否存在
from rest_framework import status
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from . import serializers
from .serializers import CreateUserSerializer, UserDetailSerializer, EmailUpdateSerializer
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
