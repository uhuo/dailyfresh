from django.contrib import admin

from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU

# 设置 首页固定不变数据 的缓存 时，要导入的 模块
from django.core.cache import cache




# Register your models here.

# 如果GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner这几个类，
# 每个类 都实现自己的save_model, delete_model方法，看起来 是有冗余的。
# 因此，把这两个方法 抽成一个类BaseModelAdmin(继承admin.ModelAdmin)。
# 再让GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner这几个类，
# 继承该BaseModelAdmin类(于是理所当然的 继承了该类的save_model, delete_model方法)
class BaseModelAdmin(admin.ModelAdmin):
    # 当后台管理员 添加/更新 数据时，会调用ModelAdmin.save_model, ModelAdmin.delete_model这两个方法
    def save_model(self, request, obj, form, change):
        '''向表中添加数据，或者 更新 表中的数据时，调用该方法'''
        # 调用父类ModelAdmin的save_model方法，完成 数据的更新
        super().save_model(request, obj, form, change)

        # 发出 更新静态页面的任务，让celery worker重新生成 首页静态页面
        # 管理员 修改 首页页面信息时，执行该函数，若在该函数中 执行其它的耗时操作，会让管理员等待 耗时操作的完成
        # 因此，需要将 耗时操作 进行异步处理。
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清除 首页部分-固定不变数据 的缓存
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        '''删除表中的数据时，调用该方法'''
        super().delete_model(request, obj)

        # 发出 更新静态页面的任务，让celery worker重新生成 首页静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        # 清除 首页部分-固定不变数据 的缓存
        cache.delete('index_page_data')


class GoodsTypeAdmin(BaseModelAdmin):
    pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass

class GoodsSKUAdmin(BaseModelAdmin):
    pass



admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)

# 将IndexPromotionBannerAdmin作为IndexPromotionBanner的 管理类
# 当管理员 修改 IndexPromotionBanner对应的数据表时，django会调用admin.ModelAdmin的save_model,delete_model
# 但是 我们不能修改ModelAdmin的源代码。我们 可以重写save_model, delete_model方法
# 并在save_model，delete_model中，添加 更新静态页面的操作
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)

admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)

admin.site.register(GoodsSKU, GoodsSKUAdmin)
