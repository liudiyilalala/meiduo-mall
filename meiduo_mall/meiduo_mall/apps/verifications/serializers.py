from rest_framework import serializers
from django_redis import get_redis_connection
"""图片验证码校验序列化器"""


class ImageCodeCheckSerializer(serializers.Serializer):
    image_code_id = serializers.UUIDField()
    text = serializers.CharField(max_length=4, min_length=4)

    def validate(self, attrs):
        image_code_id = attrs['image_code_id']
        text = attrs['text']

        # 从redis中获取真实的图片验证码
        redis_conn = get_redis_connection('verify_codes')
        real_image_code = redis_conn.get('img_%s' % image_code_id)
        if not real_image_code:
            raise serializers.ValidationError('图片验证码无效')

        # 删除获取的验证码，防止跳过前端进行重复请求
        redis_conn.delete('img_%s' % image_code_id)

        # 比较用户输入的图片验证码和真实验证码是否一致
        # 需要将获取的验证码转码
        real_image_code = real_image_code.decode()
        if text.lower() != real_image_code.lower():
            raise serializers.ValidationError("图片验证码输入错误")
        # 判断用户输入的短信验证码是否在60s内
        mobile = self.context['view'].kwargs['mobile']  # 获取对应的视图，并获取该视图url中mobile信息
        send_time = redis_conn.get('send_time_%s' % mobile)
        if send_time:
            raise serializers.ValidationError('验证码已发送，请勿重复操作')

        return attrs
