from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^users/$', views.UserRegisterView.as_view()),
    re_path(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
    re_path(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    re_path(r'^authorizations/$', obtain_jwt_token),   # 登陆认证
    re_path(r'^user/$', views.UserDetailView.as_view()),
    re_path(r'^email/$', views.EmailView.as_view()),
    re_path(r'^emails/verification/$', views.EmailVerifyView.as_view()),
]