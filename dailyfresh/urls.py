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
from django.contrib import admin
from django.urls import path

# import url, include
from django.conf.urls import include
from django.conf.urls import url



from django.urls import re_path

urlpatterns = [
    path('admin/', admin.site.urls),


    re_path(r'^search', include('haystack.urls')),  # 全文检索框架


    url(r'^tinymce/', include('tinymce.urls')), # 富文本编辑器
    #path(r'^tinymce/', tinymce.urls)

    # re_path(r'^order/', include(('order.urls', 'order'), namespace='order')),
    # re_path(r'^user/', include(('user.urls', 'user'), namespace='user')),
    # re_path(r'^cart/', include(('cart.urls', 'cart'), namespace='cart')),
    # re_path(r'^', include(('goods.urls', 'goods'), namespace='goods')),

    re_path(r'^order/', include('apps.order.urls', namespace='order')), # 订单模块
    re_path(r'^user/', include('apps.user.urls', namespace='user')),   # 用户模块
    re_path(r'^cart/', include('apps.cart.urls', namespace='cart')),   # 购物车模块
    re_path(r'^', include('apps.goods.urls', namespace='goods')),      # 商品模块

    # 以下几行的配置是按视频所教的 进行配置。
    # 当include中使用namespace时，需要传递一个元组('apps.order.urls', 'apps.order')，
    # 其中apps.order.urls指定url，apps.order指定app_name(此处仍可能 有错误)
    ####################################################################################################
    # url(r'^order/', include(('apps.order.urls', 'apps.order'), namespace='order')), # 订单模块
    # url(r'user/', include(('apps.user.urls', 'apps.user'), namespace='user')),   # 用户模块
    # url(r'^cart/', include(('apps.cart.urls', 'apps.cart'), namespace='cart')),   # 购物车模块
    #url(r'^', include(('apps.goods.urls', 'apps.goods'), namespace='goods')),       # 商品模块
]











