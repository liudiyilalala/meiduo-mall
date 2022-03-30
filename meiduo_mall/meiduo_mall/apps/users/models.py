from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from itsdangerous import TimedJSONWebSignatureSerializer as JWTSerializer, BadData

# Create your models here.
from users import contains


class User(AbstractUser):
    """用户模型类"""
    mobile = models.CharField(max_length=11, unique=True, verbose_name="手机号")
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Meta:
        db_table = "tb_users"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    # 校验token
    @staticmethod
    def check_user_token(token):
        serializer = JWTSerializer(settings.SECRET_KEY, contains.JWT_SERIALIZER_TOKEN_TIMES)
        try:
            data = serializer.loads(token)
        except BadData:
            return None
        # 从data中取出生成token的userid和email
        # 查询数据库，取出相对应的用户
        else:
            user_id = data['user_id']
            email = data['email']
            try:
                user = User.objects.get(id=user_id, email=email)
            except User.DoesNotExist:
                return None
            else:
                return user
