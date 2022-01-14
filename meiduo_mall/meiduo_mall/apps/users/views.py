from django.shortcuts import render

# Create your views here.
# 判断账号是否存在
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from . import serializers
from .serializers import CreateUserSerializer


# 注册逻辑实现
class UserRegisterView(CreateAPIView):
    # 校验参数   获取的参数： username, mobile ,password, password2, sms_code, allow
    # 保存数据
    # 返回
    # 使用序列化器实现
    serializer_class = serializers.CreateUserSerializer


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

