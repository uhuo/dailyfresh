from django.shortcuts import render
from django.views.generic import View

# 返回json，需要导入该 模块
from django.http import JsonResponse

from apps.goods.models import GoodsSKU

from django_redis import get_redis_connection

from utils.mixin import LoginRequiredMixin

# Create your views here.

# 商品添加到购物车:
# 涉及到数据的修改，采用post传参
# 只涉及到数据的捕获，采用get传参
#
# 请求方式: 采用ajax post
# 传递参数: 商品id(sku_id)，商品的数目(count)

# 地址：/cart/add
class CartAddView(View):
    '''添加 购物车记录'''
    def post(self, request):
        '''添加 购物车记录'''
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录, 请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            # 'res'：0 表示 数据不完整，'errmsg' 错误信息
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            # 数目 出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # hget(name, key), return the value of 'key' within the hash 'name'
        # 尝试获取 sku_id的值(即 查看购物车中是否有 该商品的记录)，hget(cart_userid, sku_id)
        cart_count = conn.hget(cart_key, sku_id)    # hget不会报错，hash中 不存在sku_id时 返回None
        if cart_count:
            # 购物车中 有sku_id的商品
            # 获取到了 sku_id的值，对购物车中商品的数目 进行 累加
            # 从redis中拿出的数据 均为 字符串
            # cart_count为None时，所要设置的 购物车中某商品的数量 即为count
            count += int(cart_count)

        # 校验 商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置 hash中sku_id对应的值
        # hset(name, key, value)，
        # 当sku_id不存在时 hset相当于 新增[sku_id, count]. 当sku_id存在时，hset相当于对sku_id更新
        conn.hset(cart_key, sku_id, count)

        # 计算 用户购物车中 商品的条目数
        total_count = conn.hlen(cart_key)

        # 返回 应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '添加成功',})


# 地址：/cart/
class CartInfoView(LoginRequiredMixin, View):
    '''购物车页面显示'''
    def get(self, request):
        # 获取 登陆的用户
        user = request.user

        # 获取 用户购物车中 商品的信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # hgetall(name): return a Python dict of the hash's name/value pairs
        # {'商品的id': 商品的数量}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        # 保存 用户购物车中 商品的总数目和总价格
        total_count = 0
        total_price = 0
        # 遍历cart_dict字典, 获取 商品的信息
        for sku_id, count in cart_dict.items():
            # 把 字节类型的count转为 字符串
            count = count.decode('utf8')
            # 根据商品的id 获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态地 给sku对象 增加一个amount属性, 保存对应商品的小计
            sku.amount = amount
            # 动态地 给sku对象 增加一个count属性, 保存对应商品的数量
            sku.count = count
            skus.append(sku)

            # 累加计算 商品的总数目 总价格
            total_count = total_count + int(count)
            total_price = total_price + amount

        # 组织上下文
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        }

        # 使用模板
        return render(request, 'cart.html', context)


# 更新购物车中商品的信息
# 采用ajax post请求
# 前端需要传递的参数：商品id(sku_id), 商品数量(count)
# 地址：/cart/update
class CartUpdateView(View):
    '''更新 购物车中商品的记录'''
    def post(self, request):
        '''更新 购物车中商品的记录'''
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请先登录'})
        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验 商品的数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：更新购物车中商品的记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 更新 sku_id对应的商品 的数量
        conn.hset(cart_key, sku_id, count)

        # 计算 用户购物车中商品 的 总件数
        # hvals(name): return the list of values within hash name
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count = total_count + int(val)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '更新成功',})


# 删除 购物车某个条目的记录
# 采用ajax post请求
# 前端需要传递的参数：商品id(sku_id)
# 地址：/cart/delete
class CartDeleteView(View):
    '''删除 购物车某个条目的记录'''
    def post(self, request):
        # 判断 用户是否登陆
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录，请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')

        # 数据校验
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理：删除购物车中sku_id对应条目的记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        # hdel(name, *keys): delete keys from hash name
        conn.hdel(cart_key, sku_id)

        # 计算 用户购物车中 商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count = total_count + int(val)

        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功',})




















































