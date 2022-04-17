from rest_framework.routers import DefaultRouter
from rest_framework_jwt.views import obtain_jwt_token

from . import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^users/$', views.UserRegisterView.as_view()),
    re_path(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
    re_path(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    re_path(r'^authorizations/$', views.UserAuthorizeView.as_view()),   # 登陆认证
    re_path(r'^user/$', views.UserDetailView.as_view()),
    re_path(r'^email/$', views.EmailView.as_view()),
    re_path(r'^emails/verification/$', views.EmailVerifyView.as_view()),
    re_path(r'^browse_histories/$', views.UserBrowserHistoryView.as_view()),
]

router = DefaultRouter()
router.register(r'addresses', views.AddressViewSet, basename='addresses')

urlpatterns += router.urls
# POST /addresses/ 新建  -> create
# PUT /addresses/<pk>/ 修改  -> update
# GET /addresses/  查询  -> list
# DELETE /addresses/<pk>/  删除 -> destroy
# PUT /addresses/<pk>/status/ 设置默认 -> status
# PUT /addresses/<pk>/title/  设置标题 -> title
