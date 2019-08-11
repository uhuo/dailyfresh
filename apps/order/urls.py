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

from apps.order.views import OrderPlaceView, OrderCommitView, OrderPayView, CheckPayView, CommentView
from django.urls.conf import re_path

app_name = 'order'

urlpatterns = [

    re_path(r'^place$', OrderPlaceView.as_view(), name='place'),    # 显示 提交订单页面
    re_path(r'^commit$', OrderCommitView.as_view(), name='commit'), # 创建 订单
    re_path(r'^pay$', OrderPayView.as_view(), name='pay'),  # 订单支付
    re_path(r'^check$', CheckPayView.as_view(), name='check'),  # 检测支付结果
    re_path(r'^comment/(?P<order_id>.+)$', CommentView.as_view(), name='comment'),   # 显示订单评论

]






















