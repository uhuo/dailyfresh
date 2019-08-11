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

from apps.cart.views import CartAddView, CartInfoView, CartUpdateView, CartDeleteView
from django.urls import re_path


app_name = 'cart'
urlpatterns = [

    re_path(r'^add$', CartAddView.as_view(), name='add'),   # 添加 购物车记录
    re_path(r'^$', CartInfoView.as_view(), name='show'),   # 购物车 详情页面
    re_path(r'^update$', CartUpdateView.as_view(), name='update'),  # 更新 购物车中商品的记录
    re_path(r'^delete$', CartDeleteView.as_view(), name='delete'),  # 删除 购物车中 某个条目的商品记录
]
