from django.shortcuts import render, redirect
from django.urls import reverse # 逆向解析url时，需要导入

from apps.user.models import User, Address
from apps.goods.models import GoodsSKU
from apps.order.models import OrderInfo, OrderGoods

# 加密用户信息时，需要导入的 模块
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

# 使用settings中的'SECRET_KEY'，需要导入settings
from django.conf import settings

# 返回token已过期，要导入的 模块
from django.http import HttpResponse

# 捕获 token过期 所带来的 异常
from itsdangerous import SignatureExpired

# 使用Django内置函数 发送邮件，要导入的 模块
from django.core.mail import send_mail

# 用户校验(authenticate), 保存用户登陆状态(login), (使用logout)删除当前用户的 session
from django.contrib.auth import authenticate, login, logout

# 使用celery异步函数 发邮件，需要导入
from celery_tasks.tasks import send_register_active_email

from utils.mixin import LoginRequiredMixin

from django_redis import get_redis_connection

from django.core.paginator import Paginator


# 导入正则模块
import re

from django.views.generic import View

class RegisterView(View):
    # /user/register
    # 虽然请求的url都是/user/register,
    # 但是使用 类视图：可以根据同一页面(/user/register)的不同请求(GET, POST, PUT,...),
    # 调用不同的方法
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        '''
            注册处理
            '''

        ####################################
        # 接收 客户端传来的 数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cfpasswd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        ######################################################
        # 对数据 进行校验
        if not all([username, password, cfpasswd, email]):
            # 数据不完整，返回register页面 和 ErrorMessage
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if password != cfpasswd:
            return render(request, 'register.html', {'errmsg': '密码不一致'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '未同意用户使用协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        ######################################################
        # 进行 业务处理(用户注册)
        # user = User()
        # user.username = username
        # user.password = password
        # user.email = email
        # user.save()
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        ##### 发送激活邮件，激活邮件包含：激活链接(比如http://127.0.0.1:8000/user/active/user_id)
        # 激活链接应该包含：用户身份信息
        # (用户身份信息要加密，否则拿到激活链接的用户，可能会伪造其他人的身份信息-根据自身的user_id更改为其他人的user_id
        # 对其他人进行激活)

        # 加密用户的身份信息，生成激活token
        serializer = Serializer(settings.SECRET_KEY, 3600)  # 3600秒后，加密信息过期
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # token is kind of bytes
        token = token.decode('utf8')    # 把 字节流形式的token，转为utf8形式的字符串

        ###### 发邮件

        send_register_active_email.delay(email, username, token)



        # subject = 'DailyFresh账号激活邮件'    # 邮件标题
        # message = ''                        # 邮件正文
        # sender = settings.EMAIL_FROM        # 发件人
        # receiver = [email]                  # 收件人
        # # 邮件中html格式的信息，应该传递给send_mail函数的html_message参数
        # # %s 用后面的 参数 %s(username, token, token)进行替换
        # html_message = '<h1>欢迎 %s, 您已成为天天生鲜注册会员</h1>请点击下面链接激活您的账号<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>'%(username, token, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        # # send_mail 会把邮件发送到smtp服务器，在send_mail把邮件发动到smtp服务器之前 会一直阻塞
        # # 可能会一直停滞在 注册页面，造成用户等待。


        ###### 



        ######################################################
        # 返回应答 给客户端, 跳转到首页
        return redirect(reverse('goods:index'))
        # return HttpResponseRedirect(reverse('goods:index'))


class ActiveView(View):
    '''
    用户激活
    '''
    def get(self, request, token):
        '''active user account'''
        # 解密token，获取token携带的 用户信息，来激活 用户账户
        serializer = Serializer(settings.SECRET_KEY, 3600)

        try:
            info = serializer.loads(token)
            # 获取 token所携带的 用户信息
            user_id = info['confirm']

            # 根据user_id查找 数据表中的记录，修改 相关记录的 is_active信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 激活后，跳转到 登陆页面
            rtn_result = redirect(reverse('user:login'))


        except SignatureExpired as e:
            # 激活链接 已过期
            rtn_result = HttpResponse('激活链接 已过期')
        finally:
            return rtn_result


# /user/login
class LoginView(View):
    '''
    login
    '''
    def get(self, request):
        # 显示登陆页面

        # 判断 是否记住了 用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''

        # 使用模板
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        '''登陆校验'''

        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})


        # 业务处理：校验 （用户名密码作为一条数据库中的记录），是否 存在于数据库的user表中
        user = authenticate(username=username, password=password)

        if user is not None:
            # 用户名 密码 一致
            if user.is_active:
                # 用户已激活
                # 有些页面，需要用户登陆 才能访问。因此，需要记录 用户登陆状态
                # 把 用户 保存在 django的session中(配置后，session被存在redis中)
                login(request, user)
                # 使用login后，才能使用login_required(进行 登录与否 的判断) logout(清除 request的session数据)。
                # 它们(login, login_required, logout)都是django自带认证系统中的函数，自成一套体系

                # 获取 登陆后 要跳转到 哪个地址。
                # 没有'next'参数时，默认跳转到 首页
                # next参数，在request的GET中获得
                # 若 浏览器地址栏 中的地址 含有next参数，拿到next，跳转到登陆之前的页面。地址栏中的地址 没有next时，跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))   # 没有next参数时，返回reverse('goods:index')

                # 跳转到首页
                response = redirect(next_url) # 返回对象为HttpResponseRedirect


                # 判断 是否需要 记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 记住 用户名
                    # cookie是 键值对 的形式
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

            else:
                response = render(request, 'login.html', {'errmsg':'account未激活'})
        else:
            # 用户名 或 密码 错误
            response = render(request, 'login.html', {'errmsg': '用户名或密码错误'})

        return response




        # 返回应答



# /user/logout
class LogoutView(View):
    # logout 接收 httpresponse请求
    # 即使 用户没有登录，logout也不会 抛异常
    # 调用logout后， 当前request的 会话数据 都将清除。这是为了防止：另外一个人 使用当前浏览器登入，从而访问 上一个用户的 会话数据。

    def get(self, request):
        '''退出登录，清除 用户session信息'''
        logout(request)

        return redirect(reverse('goods:index'))















# Create your views here.

# location of url: ./user/register
def register(request):
    '''register'''
    if request.method == 'GET':
        # show the register.html
        return render(request, 'register.html')
    elif request.method == 'POST':
        '''
            注册处理
            '''

        ####################################
        # 接收 客户端传来的 数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        cfpasswd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        ######################################################
        # 对数据 进行校验
        if not all([username, password, cfpasswd, email]):
            # 数据不完整，返回register页面 和 ErrorMessage
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if password != cfpasswd:
            return render(request, 'register.html', {'errmsg': '密码不一致'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '未同意用户使用协议'})

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户不存在
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        ######################################################
        # 进行 业务处理(用户注册)
        # user = User()
        # user.username = username
        # user.password = password
        # user.email = email
        # user.save()
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        ######################################################
        # 返回应答 给客户端, 跳转到首页
        return redirect(reverse('goods:index'))
        # return HttpResponseRedirect(reverse('goods:index'))

def register_handle(request):
    '''
    注册处理
    '''

    ####################################
    # 接收 客户端传来的 数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    cfpasswd = request.POST.get('cpwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    ######################################################
    # 对数据 进行校验
    if not all([username, password, cfpasswd, email]):
        # 数据不完整，返回register页面 和 ErrorMessage
        return render(request, 'register.html', {'errmsg': '数据不完整'})

    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

    if password != cfpasswd:
        return render(request, 'register.html', {'errmsg': '密码不一致'})

    if allow != 'on':
        return render(request, 'register.html', {'errmsg': '未同意用户使用协议'})

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        #用户不存在
        user = None

    if user:
        return render(request, 'register.html', {'errmsg': '用户名已存在'})


    ######################################################
    # 进行 业务处理(用户注册)
    # user = User()
    # user.username = username
    # user.password = password
    # user.email = email
    # user.save()
    user = User.objects.create_user(username, email, password)
    user.is_active = 0
    user.save()


    ######################################################
    # 返回应答 给客户端, 跳转到首页
    return redirect(reverse('goods:index'))
    #return HttpResponseRedirect(reverse('goods:index'))




# django 会使用会话session和中间件 拦截request对象到 认证系统中。
# 并给request增加一个user属性(request.user)，表示 当前的用户。
# 如果 当前用户没有登录，user属性被设置为Anonymous的一个实例。如果 当前用户登陆了，user属性 被设置为User的实例。
# 根据user的不同，is_authenticated返回不同的值：Ture 或 False

### /user
class UserInfoView(LoginRequiredMixin, View):    ### 需要 用户登陆信息的 页面，应该继承LoginRequiredMixin。以便验证 用户是否登陆
    '''用户中心-信息页'''
    def get(self, request):
        # page = 'user'，传给 base_user_center模板的 参数，根据page的值，决定高亮哪个
        # request.user.is_authenticated()
        # django会给request.user属性 赋值：1）用户已登陆，给user赋值 User的一个实例。2) 用户未登录，给user赋值 AnonymousUser的一个实例
        # 根据user的不同，is_authenticated返回不同的值：Ture 或 False
        # 除了你给 模板html文件 传递的 模板变量之外，Django框架 会把 request.user 也传递给 模板html文件.(在base模板中 使用，可影响 全部子模板)

        #################################### 获取 用户的个人信息
        user = request.user
        address = Address.objects.get_default_address(user)

        ################################# 获取 用户的 商品浏览记录################################

        # 拿redis数据库链接 的 一个方法
        # from redis import StrictRedis
        # sr = StrictRedis(host='10.211.55.15', port='6379', db=9)
        con = get_redis_connection('default')   # 也是拿到redis数据库的 一个链接。效果 和上面2行代码 一样。

        history_key = 'history_%d'%user.id

        # 获取 用户最近浏览的  五个商品的id
        sku_ids = con.lrange(history_key, 0, 4)    # 返回 一个列表(包含 五个商品id)。 l in lrange represents list

        # 从mysql数据库中 查找 五个商品的 相关信息，用于显示
        # goods_infos = GoodsSKU.objects.filter(id__in=sku_ids) # (返回的商品信息 的顺序) 和 sku_ids列表中 (商品id的 顺序) 不一致。
        # goods_rst = []
        #
        # for s_id in sku_ids:
        #     for goods in goods_infos:
        #         if s_id == goods.id:
        #             goods_rst.append(goods)

        # 遍历 sku_ids, 获取 用户浏览过的 商品信息. 下面的代码块 和 上面被注释的代码块 效果相同
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织 要传递给模板文件的信息
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}

        # 除了你给模板文件传递的 模板变量(下面一行中的{'page': 'user', 'address': address}) 之外，
        # django框架也会把 request.user 也传给 模板文件
        return  render(request, 'user_center_info.html', context)

### /user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页'''
    def get(self, request, page):
        '''显示'''
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历所有订单
        for order in orders:
            order_skus = OrderGoods.objects.filter(order=order)
            #order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历某一订单 的 所有商品，并计算 商品的小计
            for order_sku in order_skus:
                # 计算商品的小计
                amount = order_sku.count * order_sku.price
                # 动态地 给order_sku 增加属性，保存商品的小计
                order_sku.amount = amount

            # 动态地 给order 增加属性，保存该订单的 状态
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态地 给order 增加属性，保存该订单的 所有商品
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)    # 每页显示一条

        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取 第page页的 OrderInfo实例对象s
        order_page = paginator.page(page)

        # 对页码进行控制，最多显示5页
        # 1. 总页数<5，显示所有页码
        # 2. 如果 当前页是前三页，显示1-5页
        # 3. 如果 当前页是后三页，显示后五页
        # 4. 其它情况，显示 当前页的 前后2页 和 当前页
        num_pages = paginator.num_pages # 总页数
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+2+1)

        # 组织上下文
        context = {
            'order_page': order_page,
            'pages': pages,
            'page': 'order',    # 告诉 用户中心 显示哪个子页面
        }


        # 使用模板
        return  render(request, 'user_center_order.html', context)

### /user/address
class AddressView(LoginRequiredMixin, View):
    '''用户中心-地址页'''
    def get(self, request):
        # page = 'address'

        user = request.user  # 获取 登陆用户 对应的 User的实例(并不是user.models中User的实例, 可能是 django封装的)

        #try:
        #    address = Address.objects.get(user=user, is_default=True)
        #except Address.DoesNotExist:  # 没有 默认收货地址
        #    address = None
        address = Address.objects.get_default_address(user)

        # 获取 用户的 默认收货地址
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):    # 当用户 能进行 POST请求 时，用户已然 登陆了。Django会给request 增加user属性(request.user)
        '''添加 收货地址'''

        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return  render(request, 'user_center_site.html', {'errmsg': '数据不完整'})

        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式错误'})


        # 业务逻辑：添加 地址
        # 如果 用户 有 默认收货地址，添加的地址 不作为 默认收货地址

        user = request.user # 获取 登陆用户 对应的 User的实例(即是是user.models中User的实例)

        # try:    # 该user为 模型User的实例
        #    address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:    # 没有 默认收货地址
        #    address = None
        address = Address.objects.get_default_address(user)

        if address: # 有 默认收货地址，新添加的收货地址 的is_default, 应设置为False
            is_default = False
        else:   # 没有 默认收货地址，新添加的收货地址 的is_default, 应设置为True
            is_default = True

        # 构建 新地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)


        # 返回 应答
        return redirect(reverse('user:address'))    # redict的请求方式是 GET























































