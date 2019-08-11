from django.shortcuts import render, redirect
from django.urls import reverse # 逆向解析

from django.views.generic import View
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from django_redis import get_redis_connection

from apps.order.models import OrderGoods

# 使用 分页类，导入 该模块
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# 设置 首页部分-固定不变数据 的缓存，要导入该模块
from django.core.cache import cache

# Create your views here.

# http://127.0.0.1:8000/index
class IndexView(View):
    '''首页'''
    def get(self, request):

        # 尝试从缓存中 获取数据
        # 拿不到 数据时，返回 None

        context = cache.get('index_page_data')

        if context is None:
            # 缓存中 没有数据
            print('设置缓存')
            types = GoodsType.objects.all()


            goods_banners = IndexGoodsBanner.objects.all().order_by('index')
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')


            for type in types:
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

                type.image_banners = image_banners
                type.title_banners = title_banners

            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners,
            }

            # 设置 首页部分-固定不变的数据 的缓存
            # key: 缓存数据的key，value：缓存数据，timeout：缓存的 过期时间
            # timout 作用：以防goods.admin模块中 对数据表 更新的时候，没有顺带删除 首页部分固定不变数据 的缓存，
            # 而使得 首页部分固定不变数据 被永久缓存
            cache.set('index_page_data', context, 60*5)

        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        # 添加 用户相关的数据 到context字典中
        context.update(cart_count=cart_count)


        return render(request, 'index.html', context)


# /goods/商品id
class DetailView(View):
    '''详情页'''
    def get(self, request, goods_id):
        '''显示 详情页'''

        # 获取 商品种类 信息
        types = GoodsType.objects.all()

        # 获取 用户购物车中 商品数量信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户历史浏览记录
            # lrem(name, count, value)。要移除的元素 存在时，进行移除。若 要移除的元素 不存在时，什么都不做。
            # 因此，没必要 对元素存在与否 进行判断。
            # name: 指定key, count=0: 从key对应的记录中 移除所有 与value相等的值，value: 要移除的值
            conn = get_redis_connection('default')
            history_key = 'history_%d'%user.id
            # 移除后 再在 左端插入：更新浏览记录的顺序
            # 移除 列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 在列表左侧插入 goods_id
            # lpush(name, *values): push values onto the head of list 'name'
            # *values: 可以插入 多个
            conn.lpush(history_key, goods_id)
            # 只保存 用户最近浏览的 五条信息
            conn.ltrim(history_key, 0, 4)


        try:
            # get filter 区别：get只能查找满足条件的单条记录，若有多条记录 会报错
            # filter可以根据条件，返回 满足条件的结果集
            
            sku = GoodsSKU.objects.get(id=goods_id) # 根据goods_id字段，从GoodSKU表中 得到sku的一条记录

            # 获取 同spu的其它商品
            same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

            # 获取 商品的 评论
            # 根据sku，过滤OderGoods中 符合条件的 订单商品-记录s, 排除 comment为''的 记录s
            sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

            # 获取 新品信息
            # 根据sku.type 获取 同种类 商品，并根据创建时间排序(降序)
            new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]  # (默认升序)"-"降序. [:2]取开头的两个 商品

            # 组织模板上下文
            # context.update(sku=sku)
            # context.update(sku_orders=sku_orders)
            # context.update(new_skus=new_skus)
            context = {
                'sku': sku,
                'types': types,
                'same_spu_skus': same_spu_skus,
                'sku_orders': sku_orders,
                'new_skus': new_skus,
                'cart_count': cart_count,
            }

            # 使用模板
            response = render(request, 'detail.html', context)

        except GoodsSKU.DoesNotExist:
            # 商品不存在(查不到goods_id对应的商品)，跳转到 首页
            response = redirect(reverse('goods:index'))


        return response


# 种类id，页码：显示第几页的内容，以何种方式(销量/价格/人气) 排序
# 地址形式3: /list?type_id=种类id&page=页码&sort=排序方式
# 地址形式1: /list/种类id/页码/排序方式
# 地址形式2: /list/种类id/页码?sort=排序方式
# 跟在'?号'后的参数: request.get获取
# 以/分隔的 参数: 在urls.py中 捕获
# 选择 形式2：采用这种形式的原因是，在url中 以地址代表资源。/list/种类id/页码 表示 获取某个种类的第几页的资源
class ListView(View):
    '''列表页'''
    def get(self, request, type_id, page):
        '''显示列表页'''

        # 获取 某种类商品的 信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取 商品的所有分类
        types = GoodsType.objects.all()

        # 获取 排序方式，按排序方式 排序某种类的 所有商品
        # sort=default: 按默认id排序 显示
        # sort=price: 按照商品价格排序
        # sort=hot: 按照商品销量(sales)排序
        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price') # 默认升序，价格从低到高
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales') # 按销量降序 排列
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')  # 按id降序 排列

        # 对 商品数据 进行分页
        paginator = Paginator(skus, 1)  # 对skus进行分页，每页显示 1个商品

        # 获取 第page页 的内容
        try:
            page = int(page)    # 容错： 如果page转换不成字符串，默认显示 第一页的数据
        except Exception as e:
            page = 1

        if page > paginator.num_pages:  # page参数 大于 总页数
            page = paginator.num_pages
        # 获取 第page页的 Page实例对象
        skus_page = paginator.page(page)

        # page = int(page)
        # try:
        #     skus_page = paginator.page(page)
        # except PageNotAnInteger:
        #     # page is not an integer
        #     skus_page = paginator.page(1)
        # except EmptyPage:
        #     # page is out of range
        #     skus_page = paginator.page(paginator.num_pages)

        # 控制 页码最多显示5个，并且显示 当前页的前两页和后两页
        # 1.总页数<5, 显示所有页码
        # 2.如果 当前页是1，2，3时，显示 1 2 3 4 5 页
        # 3.如果 当前页是最后3页，显示 最后5页
        # 其它情况，显示当前页的 前2页, 当前页, 和 当前页的后2页.
        # num_pages：总页码。page：当前页。pages：页码范围

        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)   # 前包 后不包，所以写成 1， num_pages+1
        elif page <=3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+2+1)


        # 获取 新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取 购物车信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        # 组织 模板上下文
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort,
            'pages': pages,
        }

        # 使用模板
        return render(request, 'list.html', context)





























































