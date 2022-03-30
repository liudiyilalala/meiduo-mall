from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from oauth.utils import OauthQQ
from users.models import User


class OauthQQAPIViewSerializer(serializers.ModelSerializer):
    """
        保存QQ用户序列化器
        """
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='操作凭证', write_only=True)
    token = serializers.CharField(read_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'sms_code', 'mobile', 'access_token', 'token']

        extra_kwargs = {
            'username': {
                'read_only': True,
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

    def validate(self, attrs):
        # 校验access_token
        access_token = attrs['access-token']
        openid = OauthQQ.check_user_token(access_token)
        if not openid:
            raise serializers.ValidationError("无效的access_token")

        # 将openid保存到attrs中
        attrs['openid'] = openid

        # 校验短信验证码是否正确
        mobile = attrs['mobile']
        sms_code = attrs['sms_code']
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_code_%s' % mobile)
        if sms_code != real_sms_code.decode():
            raise serializers.ValidationError("短信验证码输入不正确")

        # 如果用户存在，校验密码是否正确
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError("密码输入不正确")
            # 设置用户与openid
            attrs['user'] = user

        return attrs

    def create(self, validated_data):

        mobile = validated_data['mobile']
        password = validated_data['password']
        openid = validated_data['openid']
        user = validated_data.get('user')

        if not user:
            # 如果用户不存在，则创建用户，保存openid
            user = user.objects.create_user(username=mobile, mobile=mobile, password=password)

        OAuthQQUser.object.create(user=user, openid=openid)

        # 签发jwt token
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)

        user.token = token

        # self.context['view'].user = user
        return user
