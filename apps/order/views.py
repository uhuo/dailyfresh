from django.shortcuts import render, redirect

# 逆向解析url时, 需要导入 该模块
from django.urls import reverse

from django.views.generic import View

from apps.goods.models import GoodsSKU

from django_redis import get_redis_connection

from apps.user.models import Address

from utils.mixin import LoginRequiredMixin

from django.http import JsonResponse

from apps.order.models import OrderInfo, OrderGoods

# 创建订单id 需要该模块
from datetime import datetime

# 保证一组sql语句的 原子性，导入该模块
from django.db import transaction

from alipay import AliPay

# 拼接路径 需要导入的模块
from django.conf import settings
import os


# Create your views here.


# 地址: /order/place
class OrderPlaceView(LoginRequiredMixin, View):
    '''显示 订单提交-页面'''
    def post(self, request):
        '''显示 订单提交-页面'''

        # 获取 登陆的用户
        user = request.user

        # 获取 参数sku_ids.
        # form表单有多个ul->input标签 input标签(name="sku_ids" value="{{ sku.id }}").
        # 从form表单 getlist('sku_ids'), 获取到的 是个列表.
        sku_ids = request.POST.getlist('sku_ids')

        # 校验参数
        if not sku_ids:
            return redirect(reverse('cart:show'))

        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        skus = []
        # total_count, total_price 分别保存 商品的 总件数 总价格
        total_count = 0
        total_price = 0

        # 遍历sku_ids 获取 用户要购买的商品sku
        for sku_id in sku_ids:
            # 根据商品的id 获取 商品的sku
            sku = GoodsSKU.objects.get(id=sku_id)
            # 从redis中 获取 商品的数量
            count = conn.hget(cart_key, sku_id)

            # 以防用户刷新 提交订单 页面，出现报错
            if count is None:
                return redirect(reverse('goods:index'))

            ########### count.decode  ###########
            # count = count.decode('utf8')

            # 计算 商品的小计
            amount = sku.price * int(count)

            # 动态给sku增加属性count, 保存 商品的数量
            # 动态给sku增加属性amount, 保存 商品的小计
            sku.count = int(count)
            sku.amount = amount

            skus.append(sku)

            # 累加计算 商品的 总件数 总价格
            total_count = total_count + int(count)
            total_price = total_price + amount

        # 运费：实际生产中，属于一个子系统。可以 建个表，根据 价格区间 来区分 运费
        transit_price = 10  # 运费固定

        # 实付款
        total_pay = total_price + transit_price

        # 获取 用户收货地址
        addrs = Address.objects.filter(user=user)

        # 组织上下文
        sku_ids = ','.join(sku_ids) # [3, 1, 6, 39] -> 3,1,6,39
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'sku_ids': sku_ids,
        }

        # 使用模板
        return render(request, 'place_order.html', context)



# 前端传递的参数：地址id(addr_id), 支付方式(pay_method), 用户要购买的商品id(sku_ids字符串)
# 该页面也需要 用户登陆。post函数 涉及ajax，所以 不能采用LoginRequiredMixin。转而 采用 user.is_authenticated
class OrderCommitView1(View):
    '''创建 订单'''
    # 对post方法 使用@transaction.atomic进行装饰。
    # post方法中 涉及数据库的操作 就被放到一个事务中，从而保证 该事务中所有sql语句 的原子性。
    @transaction.atomic
    def post(self, request):
        '''创建 订单'''
        # 判定用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请先登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '联系地址中 没有 该地址'})

        # savepoint(using=None): 创建保存点。返回值是savepoint ID (sid).
        # savepoint_commit(sid, using=None): 提交保存点之前的操作，释放sid。从保存点起，所有的操作 成为 一个新的事务，保存点之前的操作 不再算做 新事务的一部分。
        # savepoint_rollback(sid, using=None): 回滚事务至保存点sid。

        # todo: 核心业务：创建订单
        # 订单信息表：df_order_info 订单商品表：df_order_goods
        # 创建一条订单：需要向df_order_info中 加入一条记录，需要(根据商品条目数) 向df_order_goods中 添加若干条记录
        # 创建订单时，先要向df_order_info中 添加记录，再向 df_order_goods中 添加记录。
        # 因为 df_order_goods中 有字段 外键依赖df_order_info。

        # 组织OrderInfo所需参数：order_id, total_count, total_price, transit_price
        # 订单id：采用年月日时分秒 字符串。20190807104631 + user.id(加上user.id 保证 订单id唯一)
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        transit_price = 10

        # 商品总数目total_count, 商品总金额total_price
        total_count = 0
        total_price = 0

        # 设置保存点
        save_id = transaction.savepoint()
        try:
            # todo：向df_order_info中 添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            # todo: 根据用户订单中 商品的条目数 向df_order_goods中 添加若干条记录
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                try:
                    # 查询数据时 加锁。事务结束时 释放 锁。
                    # select * from df_goods_sku where id = sku_id for update;
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # print('user:%d, stock:%d'%(user.id, sku.stock))
                # import time
                # time.sleep(10)

                # 从redis中获取 订单中 某条目商品 的数量
                count = conn.hget(cart_key, sku_id)

                # todo: 判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # todo: 向df_order_goods中 添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # todo: 更新 对应商品的库存和销量
                sku.stock = sku.stock - int(count)
                sku.sales = sku.sales + int(count)
                sku.save()

                # todo: 累加计算 商品的总数目和总价格
                total_count = total_count + int(count)
                amount = sku.price * int(count)
                total_price = total_price + amount

            # 更新 订单信息表df_order_info 的总数量 和 总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo: 清除 用户购物车中的记录
        # hdel(name, *keys): delete keys from hash name
        conn.hdel(cart_key, *sku_ids)   # *[1, 3, 6, 11]：解包列表，作为 位置参数

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})



class OrderCommitView(View):
    '''创建 订单'''
    # 对post方法 使用@transaction.atomic进行装饰。
    # post方法中 涉及数据库的操作 就被放到一个事务中，从而保证 该事务中所有sql语句 的原子性。
    @transaction.atomic
    def post(self, request):
        '''创建 订单'''
        # 判定用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请先登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '联系地址中 没有 该地址'})

        # savepoint(using=None): 创建保存点。返回值是savepoint ID (sid).
        # savepoint_commit(sid, using=None): 提交保存点之前的操作，释放sid。从保存点起，所有的操作 成为 一个新的事务，保存点之前的操作 不再算做 新事务的一部分。
        # savepoint_rollback(sid, using=None): 回滚事务至保存点sid。

        # todo: 核心业务：创建订单
        # 订单信息表：df_order_info 订单商品表：df_order_goods
        # 创建一条订单：需要向df_order_info中 加入一条记录，需要(根据商品条目数) 向df_order_goods中 添加若干条记录
        # 创建订单时，先要向df_order_info中 添加记录，再向 df_order_goods中 添加记录。
        # 因为 df_order_goods中 有字段 外键依赖df_order_info。

        # 组织OrderInfo所需参数：order_id, total_count, total_price, transit_price
        # 订单id：采用年月日时分秒 字符串。20190807104631 + user.id(加上user.id 保证 订单id唯一)
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        transit_price = 10

        # 商品总数目total_count, 商品总金额total_price
        total_count = 0
        total_price = 0

        # 设置保存点
        save_id = transaction.savepoint()
        try:
            # todo：向df_order_info中 添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            # todo: 根据用户订单中 商品的条目数 向df_order_goods中 添加若干条记录
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 乐观锁 对 商品记录的更新  进行三次尝试
                for i in range(3):
                    try:
                        # 乐观锁：查询数据时 不加锁。
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    # 从redis中获取 订单中 某条目商品 的数量
                    count = conn.hget(cart_key, sku_id)

                    # todo: 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # todo: 更新 对应商品的库存和销量
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # print('user:%d, times:%d, stock:%d'%(user.id, i, sku.stock))
                    # import time
                    # time.sleep(10)

                    # update df_goods_sku set stock=new_stock sales=new_sales
                    # where id=sku_id and stock=origin_stock
                    # res: 返回 受影响的行数。并发时，对该记录的修改 一定 一个先一个后(不可能真正的同时)。
                    # 若GoodsSKU.objects.filter(id=sku_id, stock=origin_stock) 过滤不到数据，就不进行update(stock=new_stock, sales=new_sales)更新
                    # 如果 数据stock发生变化，GoodsSKU.objects.filter(id=sku_id, stock=origin_stock)就过滤不到数据
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        # 第三次尝试 更新商品记录。修改商品记录时 还是发现 某商品记录的stock发生了变化，就认定 下单失败
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败2'})
                        # 不是第三次，则 再次尝试 更新商品记录
                        continue

                    ################## 向df_order_goods中 添加记录，与尝试更新 商品记录 的顺序，不能颠倒。
                    # 否则 多次尝试时 会多次向df_order_goods添加 记录相同的 重复数据。

                    # todo: 向df_order_goods中 添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # todo: 累加计算 商品的总数目和总价格
                    total_count = total_count + int(count)
                    amount = sku.price * int(count)
                    total_price = total_price + amount

                    # 能执行到这里 说明 已经对商品的记录 成功地进行了 更新。直接跳过 余下的循环次数
                    break

            # 更新 订单信息表df_order_info 的总数量 和 总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo: 清除 用户购物车中的记录
        # hdel(name, *keys): delete keys from hash name
        conn.hdel(cart_key, *sku_ids)   # *[1, 3, 6, 11]：解包列表，作为 位置参数

        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})




# ajax post
# 前端传递的参数: 订单id(order_id)
# 地址 /order/pay
class OrderPayView(View):
    '''订单支付'''
    def post(self, request):
        '''订单支付'''
        # 判断用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            # 以order_id，user查找到的 订单信息，支付方式 必须是支付宝，支付状态 必须是 未支付。才是 可提交给支付宝 的订单。
            order = OrderInfo.objects.get(order_id=order_id,
                                  user=user,
                                  pay_method=3,
                                  order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python-alipay-sdk 调用支付宝的支付接口
        # 初始化
        private_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        pulic_path = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(pulic_path).read()
        alipay = AliPay(
            appid="2016101000654275",   # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",    # RSA 或者 RSA2
            debug = True  # 默认False
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string

        # alipay.api_alipay_trade_page_pay()默认会把参数 转成json.
        # 而Decimal是不能被序列化的，所以 直接写total_amount = total_pay会报错，需要转成字符串str(total_pay)。
        total_pay = order.total_price + order.transit_price

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_pay), # 需要支付的 总金额
            subject='天天生鲜%s'%order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})





# ajax post
# 前端传递的参数: 订单id(order_id)
# 地址 /order/check
class CheckPayView(View):
    '''查看订单支付的结果'''
    def post(self, request):
        '''查询支付结果'''
        # 用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请先登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单id'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用python-alipay-sdk 调用支付宝的支付接口
        # 初始化
        private_path = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        pulic_path = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')
        app_private_key_string = open(private_path).read()
        alipay_public_key_string = open(pulic_path).read()
        alipay = AliPay(
            appid="2016101000654275",  # 应用id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用 支付宝的交易查询 接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            # response = {
            #     "alipay_trade_query_response": {
            #         "trade_no": "2017032121001004070200176844",   # 支付宝的交易号
            #         "code": "10000",                              # 接口调用 是否成功
            #         "invoice_amount": "20.00",
            #         "open_id": "20880072506750308812798160715407",
            #         "fund_bill_list": [
            #             {
            #                 "amount": "20.00",
            #                 "fund_channel": "ALIPAYACCOUNT"
            #             }
            #         ],
            #         "buyer_logon_id": "csq***@sandbox.com",
            #         "send_pay_date": "2017-03-21 13:29:17",
            #         "receipt_amount": "20.00",
            #         "out_trade_no": "out_trade_no15",
            #         "buyer_pay_amount": "20.00",
            #         "buyer_user_id": "2088102169481075",
            #         "msg": "Success",
            #         "point_amount": "0.00",
            #         "trade_status": "TRADE_SUCCESS",              # 支付结果
            #         "total_amount": "20.00"
            #     },
            #     "sign": ""
            # }

            code = response.get('code')
            trade_status = response.get('trade_status')

            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')

                # 更新 订单的状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()

                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})

            elif code == '40004' or (code == '10000' and trade_status == 'WAIT_BUYER_PAY'):
                # code == 40004 并不是错误 而是查询业务-处理失败，如果 等待用户支付完成后 再次查询 还是能查询到-支付成功
                # 等待买家付款
                import time
                time.sleep(5)

                continue

            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})




class CommentView(LoginRequiredMixin, View):
    '''订单评论'''
    def get(self, request, order_id):
        '''提供评论页面'''
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 根据订单的状态 获取 订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品小计
            amount = order_sku.price * order_sku.count
            # 动态地给order_sku增加属性amount，保存商品小计
            order_sku.amount =amount

        # 动态地给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, 'order_comment.html', {'order': order})

    def post(self, request, order_id):
        '''处理评论内容'''
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        # 获取商品数目, 也即 商品评论的条数
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        # 循环获取 订单中各个商品的评论信息 并设置商品的评论信息，没有评论信息时 跳过该评论的设置 继续下一个商品
        for i in range(1, total_count+1):
            sku_id = request.POST.get('sku_%d' % i)

            # 获取 商品的评论内容, 拿不到时评论内容时 返回空字符串
            content = request.POST.get('content_%d' % i, '')

            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 交易已完成
        order.save()

        return redirect(reverse('user:order', kwargs={"page": 1}))











































