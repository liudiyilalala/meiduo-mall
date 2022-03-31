import json
import logging
from urllib.parse import urlencode, parse_qs
from urllib.request import urlopen

from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer, BadData

# 创建qq辅助工具类
from oauth import contains
from oauth.exceptions import QQAPIError

logger = logging.getLogger('django')


class OauthQQ(object):

    def __init__(self, client_id=None, client_secret=None, redirect_uri=None, state=None):
        self.client_id = client_id or settings.QQ_CLIENT_ID
        self.client_secret = client_secret or settings.QQ_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.QQ_CLIENT_SECRET
        self.state = state or settings.QQ_STATE

    # 创建生成qq登录url方法
    def get_qq_login_url(self):

        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': self.state,
            'scope': 'get_user_info'
        }

        url = 'https://graph.qq.com/oauth2.0/authorize?' + urlencode(params)

        return url

    # 通过code获取access token
    def get_access_token(self, code):

        params = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        }

        url = 'https://graph.qq.com/oauth2.0/token?' + urlencode(params)

        # access_token=FE04************************CCE2&expires_in=7776000&refresh_token=88E4************************BE14
        # 通过urlopen方法发送http get请求，返回response响应，可以通过read()读出响应体内容
        response = urlopen(url)
        response_data = response.read().decode()
        # 将读出的内容通过parse_qs方法转为python字典
        data = parse_qs(response_data)

        access_token = data.get('access_token')
        if not access_token:
            logger.error("code=%s msg=%s" % (data.get('code'), data.get('msg')))
            raise QQAPIError
        return access_token[0]

    # 通过access_token获取open_id
    def get_open_id(self, access_token):

        url = 'https://graph.qq.com/oauth2.0/me?access_token' + access_token

        response = urlopen(url)
        response_data = response.read().decode()
        # 返回的数据 callback( {"client_id":"YOUR_APPID","openid":"YOUR_OPENID"} );
        try:
            data = json.loads(response_data[10:-4])
        # 如果失败将转为字典，输出错误
        except Exception as e:
            data = parse_qs(response_data)
            logger.error("code=%s msg=%s" % (data.get('code'), data.get('msg')))
            raise QQAPIError

        open_id = data.get('openid')
        return open_id

    # 生成保存用户数据的token
    @staticmethod
    def generate_save_user_token(self, open_id):
        # 使用itsdangrous的TimedSerializer可以生成带有效期的token
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, contains.JWT_SERIALIZER_TOKEN_TIMES)
        token = serializer.dumps({'open_id': open_id})
        token = token.decode()
        return token

    # 校验生成的token是否正确
    @staticmethod
    def check_user_token(self, access_token):
        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, contains.JWT_SERIALIZER_TOKEN_TIMES)
        try:
            data = serializer.loads(access_token)
        except BadData:
            return None
        else:
            return data['openid']

