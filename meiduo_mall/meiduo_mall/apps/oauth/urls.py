from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^oauth/qq/authorization/$', views.OauthQQUrlView.as_view()),
    re_path(r'^oauth/qq/user/$', views.OauthQQUrlView.as_view()),
]