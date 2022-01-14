import re

from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from .models import User


class CreateUserSerializer(serializers.ModelSerializer):
    # 获取的参数： username, mobile, password, password2, sms_code, allow
    password2 = serializers.CharField(label='确认密码', write_only=True)  # write_only 反序列化时校验
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    allow = serializers.CharField(label='同意协议', write_only=True)
    token = serializers.CharField(label='jwt token', read_only=True)

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






