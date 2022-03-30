from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.settings import api_settings

from .exceptions import QQAPIError
from .models import OAuthQQUser
from oauth.utils import OauthQQ
from .serializers import OauthQQAPIViewSerializer

"""qq登录的逻辑实现：
接口一： 前端点击qq登录按钮请求，后端需要返回qq的登录页面 get请求  next参数(登录成功后的跳转页面)

用户登录成功后，qq会将用户重定向到服务器的callback(oauth_callback.html)页面，并带上code和state  state就是next参数
接口二： 前端登录成功后，会向后端请求callback页面，后端通过code向qq服务器获取access_token，凭借access_token向qq请求用户的open_id
判断用户是否第一次使用qq登录
如果不是第一次使用qq登录，直接登录成功，返回jwt，并跳转到state指定的页面
如果是第一次登录，就生成绑定用户的access token并返回

接口三：前端携带手机号，密码，短信验证码，access_token请求绑定qq用户身份
检验token是否正确
检验短信验证码，用户，密码是否正确或是否存在
如果用户存在数据库，直接绑定
如果用户不存在数据库，则创建用户并绑定
返回jwt，并跳转到state页面
"""


# 接口一： 前端点击qq登录按钮请求，后端需要返回qq的登录页面 get请求  next参数(登录成功后的跳转页面)
# GET /oauth/qq/authorization/?next=xxx
class OauthQQUrlView(APIView):
    def get(self, request):
        # 获取参数
        # 校验参数
        state = request.query_params.get('next')
        # 生成qq登录页面的url
        oauth = OauthQQ(state=state)
        qq_login_url = oauth.get_qq_login_url()
        # 返回
        return Response({'login_url': qq_login_url})


class OauthQQCreateUserView(CreateAPIView):

    serializer_class = OauthQQAPIViewSerializer

    def get(self, request):
        # 获取参数
        code = request.query_params.get('code')
        # 校验参数
        if not code:
            return Response({"message": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)
        # 生成access_token
        oauth = OauthQQ()
        try:
            access_token = oauth.get_access_token(code)
            # 生成open_id
            open_id = oauth.get_open_id(access_token)
        except QQAPIError:
            return Response({'message': '调用qq接口异常'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # 判断用户是否第一次使用qq登录
        try:
            oauth_qq_user = OAuthQQUser.objects.get(openid=open_id)
        except OAuthQQUser.DoesNotExist:
            # 如果用户不存在，处理open_id，并返回
            token = oauth.generate_save_user_token(open_id)
            return Response({'access_token': token})
        else:
            # 代表用户存在，返回jwt和用户信息
            # 签发 jwt token
            user = oauth_qq_user.user
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            response = Response({
                'username': user.username,
                'user_id': user.id,
                'token': token
            })
            return response

    # def post(self, request, *args, **kwargs):
    #     pass


