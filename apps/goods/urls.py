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

from apps.goods.views import IndexView, DetailView, ListView

from django.urls import re_path


app_name = 'goods'
urlpatterns = [

    #url(r'^$', views.index, name='index'),
    re_path(r'^index/$', IndexView.as_view(), name='index'),  # 首页url
    re_path(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'), # 详情页url
    re_path(r'list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'),  # 列表页

]
