# 从celery包中，导入Celery类
from celery import Celery

# 使用settings中的'SECRET_KEY','EMAIL_FROM'，需要导入settings
from django.conf import settings


# 使用Django内置函数 发送邮件，要导入的 模块
from django.core.mail import send_mail

# # woker中，要添加Django环境 初始化 的代码
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

import os

# 下面一行导入的包，要放在Django环境初始化的代码 的后面。不然，会找不到这些类 而报错。
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
from django_redis import get_redis_connection

# 使用模板时，要导入的 模块
# 定义 模板上下文，要用RequestContext
from django.template import loader, RequestContext


# 创建一个Celery类的实例
celery_app = Celery('celery_tasks.tasks', broker='redis://10.211.55.15:6379/8')


# 定义 任务函数
# 使用celery实例 的 task方法，给send_register_active_email封装 必要的信息(如Redis数据库的ip和数据库名称)
@celery_app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    # 组织邮件信息
    subject = 'DailyFresh账号激活邮件'  # 邮件标题

    message = '123zheng-wen321'  # 邮件正文

    sender = settings.EMAIL_FROM  # 发件人
    receiver = [to_email]  # 收件人
    # 邮件中html格式的信息，应该传递给send_mail函数的html_message参数
    # %s 用后面的 参数 %s(username, token, token)进行替换
    html_message = '<h1>欢迎 %s, 您已成为天天生鲜注册会员</h1>请点击下面链接激活您的账号<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
    username, token, token)

    send_mail(subject, message, sender, receiver, html_message=html_message)


# 使用Celery对象实例的 task方法，给generate_static_index_html封装 必要的信息(如Redis数据库的ip和数据库名称)
@celery_app.task
def generate_static_index_html():
    '''产生 首页静态页面'''

    # 获取 商品的种类
    types = GoodsType.objects.all()

    # 获取 轮播商品
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取 促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取 分类商品
    for type in types:  # GoodsType

        # 获取 含图片的 分类商品
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取 含文字的 分类商品
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态的给type增加属性，保存 含图片的分类商品 和 含文字的分类商品
        type.image_banners = image_banners
        type.title_banners = title_banners

        # # 获取 用户购物车中 商品的数目
        # user = request.user
        # cart_count = 0
        # if user.is_authenticated():
        #     # 用户已登录
        #     conn = get_redis_connection('default')
        #     cart_key = 'cart_%d'%user.id
        #     cart_count = conn.hlen(cart_key)

    # 组织上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners,
                #'cart_count': cart_count,
    }


    # 使用模板
    # 1.加载模板文件, 返回 模板对象
    temp = loader.get_template('static_index.html')

    # 2.定义模板上下文, 该步骤 可以省略
    # context = RequestContext(request, context)

    # 使用context中参数，替换 模板对象中模板文件(static_index.html)的 模板变量。返回 替换后的内容(模板文件)。
    # 3.模板渲染(产生 一个替换后的内容)
    static_index_html = temp.render(context)    # 对应 静态页面的 内容

    # 用static_index_html(静态页面的 内容) 生成 首页的静态html文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')    # 生成 静态文件的 路径

    # 创建 静态文件
    with open(save_path, 'w') as f:
        f.write(static_index_html)
























































