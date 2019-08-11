"""dailyfresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls import url
from django.urls import path, re_path


from apps.user import views

from apps.user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView

from django.contrib.auth.decorators import login_required

app_name = 'user'
urlpatterns = [

    re_path(r'^register$', RegisterView.as_view(), name='register'),       # 注册

    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),       # active user account

    re_path(r'^login/$', LoginView.as_view(), name='login'), # 登陆页面
    re_path(r'^logout/$', LogoutView.as_view(), name='logout'),  # 注销 登录

    # re_path(r'^register$', views.register, name='register'),  # 用户注册页面url
    # re_path(r'^register_handle$', views.register_handle, name='register_handle'),     # 注册处理

    ################################################################################################
    ###### 访问一个地址时：如果 用户未登录(session中没有该用户信息)，
    ###### login_required会(根据配置LOGIN_URL = '/user/login/') 跳转到 登陆页面。
    ###### 并且 在登陆页面的地址后 添加next参数。next参数 是 之前访问的地址 的 路径
    ###### 如果 用户已经登陆(session中 有该用户信息)，执行login_required包裹的 视图view
    ######
    ###### 这样写(login_required(UserInfoView.as_view()))显得有些啰嗦,
    ###### 将login_required(as_view)封装在LoginRequiredMixin中,
    ###### 并让UserInfoView, UserOrderView, AddressView等 需要登录才能访问的页面，继承LoginRequiredMixin
    ###### (LoginRequiredMixin要在 子类的继承顺序 的 第一位)

    # re_path(r'^$', login_required(UserInfoView.as_view()), name='user'),     # 用户中心 信息页#######################有可能重名。。。
    # re_path(r'^order/$', login_required(UserOrderView.as_view()), name='order'),      # 用户中心 订单页
    # re_path(r'^address/$', login_required(AddressView.as_view()), name='address'),    # 用户中心 地址页
    re_path(r'^$', UserInfoView.as_view(), name='user'),    # 用户中心 信息页
    re_path(r'^order/(?P<page>\d+)$', UserOrderView.as_view(), name='order'),    # 用户中心 订单页
    re_path(r'^address/$', AddressView.as_view(), name='address')   # 用户中心 地址页


]
























