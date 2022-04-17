import re

from django.conf import settings
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from goods.models import SKU
from . import contains
from .models import User, Address
from celery_tasks.email.tasks import sen_email


class CreateUserSerializer(serializers.ModelSerializer):
    # 获取的参数： username, mobile, password, password2, sms_code, allow
    password2 = serializers.CharField(label='确认密码', write_only=True)  # write_only 反序列化时校验
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='jwt token', read_only=True)  # read_only 序列化时校验，即返回前端的数据

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow', 'token']

        extra_kwargs = {
            'username': {
                'min_length': 5,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            # 设置确认密码为反序列化时校验使用
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    # 验证手机号是否符合要求
    def validate_mobile(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError("手机号格式错误")
        return value

    def validate(self, attrs):

        # 验证两次输入的密码是否一致
        password = attrs['password']
        password2 = attrs['password2']
        if password != password2:
            raise serializers.ValidationError("两次密码输入不一致")

        # 验证短信验证码是否输入正确
        mobile = attrs['mobile']
        sms_code = attrs['sms_code']
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_code_%s' % mobile)
        if sms_code != real_sms_code.decode():
            raise serializers.ValidationError("短信验证码输入不正确")

        return attrs

    # 验证用户是否同意协议
    def validate_allow(self, value):
        if value != 'true':
            raise serializers.ValidationError("请同意用户协议")
        return value

    # 创建用户
    def create(self, validated_data):
        # 删除创建用户模型不需要的字段
        del validated_data['sms_code']
        del validated_data['allow']
        del validated_data['password2']

        # 创建用户模型
        user = User.objects.create(**validated_data)

        # 将密码加密之后保存
        user.set_password(validated_data['password'])
        user.save()

        # 签发 jwt token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        user.token = token
        # 返回用户模型即可
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """
    用户详情信息序列化器,用户序列化返回
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'mobile', 'email', 'email_active']


class EmailUpdateSerializer(serializers.ModelSerializer):
    """
    用户详情页面保存邮箱序列化器
    """
    class Meta:
        model = User
        fields = ['id', 'email']
        extra_kwargs = {
            'email': {
                'required': True   # 在反序列化时必须输入，前端传入的参数
            }
        }

    def update(self, instance, validated_data):
        email = validated_data['email']

        # 将email更新到数据库中
        instance.email = email
        instance.save()

        # 生成激活url，使用token作为链接的参数
        serializer = Serializer(settings.SECRET_KEY, contains.JWT_SERIALIZER_TOKEN_TIMES)
        token = serializer.dumps({'user_id': instance.id, 'email': email})
        token = token.decode()
        verify_url = 'http://127.0.0.1:5500/success_verify_email.html?token=' + token

        # 向该邮箱发送激活邮件的url,使用celery发送
        sen_email.delay(email, verify_url)

        return instance


class UserAddressSerializer(serializers.ModelSerializer):
        """
        用户地址序列化器
        """
        province = serializers.StringRelatedField(read_only=True)
        city = serializers.StringRelatedField(read_only=True)
        district = serializers.StringRelatedField(read_only=True)
        province_id = serializers.IntegerField(label='省ID', required=True)
        city_id = serializers.IntegerField(label='市ID', required=True)
        district_id = serializers.IntegerField(label='区ID', required=True)

        class Meta:
            model = Address
            exclude = ('user', 'is_deleted', 'create_time', 'update_time')  # 不包含序列化的字段

        def validate_mobile(self, attrs):
            if not re.match(r'^1[3-9]\d{9}$', attrs):
                raise serializers.ValidationError("手机号格式错误")
            return attrs

        def create(self, validated_data):
            # 把user保存到数据中返回,保存地址需要用户信息
            validated_data['user'] = self.context['request'].user
            return super().create(validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """
    class Meta:
        model = Address
        fields = ('title', )


class AddUserBrowserHistorySerializer(serializers.Serializer):
    """
     保存用户浏览历史记录
    """
    sku_id = serializers.IntegerField(label="商品SKU编号", min_value=1)

    # 进行sku_id字段验证
    def validate_sku_id(self, attrs):
        try:
            SKU.objects.get(id=attrs)
        except Exception as e:
            raise serializers.ValidationError("该商品不存在")
        else:
            return attrs

    # 保存sku_id到redis中
    def create(self, validated_data):
        sku_id = validated_data['sku_id']
        # 获取用户对象
        user = self.context['request'].user
        # 建立redis链接,使用管道
        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        # 去重，将redis中之前保存的sku_id对应的该条历史记录删掉
        pl.lrem("history_%s" % user.id, 0, sku_id)
        # 将当前浏览的记录保存到redis的列表第一位  history_user_id : [now_sku_id, 1, 2, 3]
        pl.lpush("history_%s" % user.id, sku_id)
        # 截断 只保存前五条记录
        pl.ltrim("history_%s" % user.id, 0, 4)

        pl.execute()
        return validated_data



