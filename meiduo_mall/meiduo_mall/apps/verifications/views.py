import logging
import random

from meiduo_mall.libs.captcha.captcha import captcha
from django.http import HttpResponse
from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from verifications import constants
from .serializers import ImageCodeCheckSerializer
from rest_framework.generics import GenericAPIView
from meiduo_mall.utils.yuntongxun.sms import CCP
from celery_tasks.sms.tasks import send_sms_code

# Create your views here.

logger = logging.getLogger('django')


class ImageCodeView(APIView):
    """图片验证码"""

    def get(self, request, image_code_id):

        # 生成图片验证码     # text表示图片验证码的内容 xxxx  # image 图片验证码的图片➕内容
        name, text, image = captcha.generate_captcha()

        # 保存图片验证码到redis中
        redis_conn = get_redis_connection("verify_codes")
        redis_conn.setex("img_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        # 将图片验证返回前端
        return HttpResponse(image, content_type="images/jpg")


class SMSCodeView(GenericAPIView):
    """短信验证码实现"""

    serializer_class = ImageCodeCheckSerializer

    def get(self, request, mobile):

        # 校验参数 使用序列化器进行校验
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 生成短信验证码
        sms_code = '%06d' % random.randint(0, 99999)

        # 使用redis管道将短信验证码和短信验证码有效期保存到redis中
        redis_conn = get_redis_connection('verify_codes')
        pl = redis_conn.pipeline()
        pl.setex("sms_code_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("send_time_%s" % mobile, constants.SMS_CODE_SEND_TIME, 1)
        pl.execute()

        # # 发送短信验证码
        # try:
        #     ccp = CCP()
        #     sms_code_period = constants.SMS_CODE_REDIS_EXPIRES // 60
        #     result = ccp.send_template_sms(mobile, [sms_code, sms_code_period], constants.SMS_CODE_TEMP_ID)
        # except Exception as e:
        #     logger.error('发送短信验证码[异常][ mobile: %s, message: %s]' % (mobile, e))
        #     return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     if result == 0:
        #         logger.info('发送短信验证码[成功][ mobile: %s ]' % mobile)
        #         return Response({'message': 'ok'})
        #     else:
        #         logger.warning('发送短信验证码[失败][ mobile: %s ]' % mobile)
        #         return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 使用celery发送短信验证码
        period = constants.SMS_CODE_REDIS_EXPIRES // 60
        send_sms_code.delay(mobile, sms_code, period, constants.SMS_CODE_TEMP_ID)

        return Response({'message': 'ok'})
