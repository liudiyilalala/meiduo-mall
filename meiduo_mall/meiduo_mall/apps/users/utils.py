import re

from django.contrib.auth.backends import ModelBackend

from users.models import User


def jwt_response_payload_handler(token, user=None, request=None):
    """
    自定义jwt认证成功返回数据
    """
    return {
        'token': token,
        'user_id': user.id,
        'username': user.username
    }


# 自定义用户输入的username是用户名或手机号
def get_user_by_account(account):
    try:
        if re.match('^1[3-9]\d{9}$', account):
            # 账号是手机号，通过手机号查找
            user = User.objects.get(mobile=account)
        else:
            # 账号是用户名登陆
            user = User.objects.get(username=account)
    except Exception as e:
        return None
    else:
        return user


# 自定义用户名或密码登陆
class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):

        # 获取参数
        user = get_user_by_account(username)
        # 校验参数
        if user and user.check_password(password):
            return user
