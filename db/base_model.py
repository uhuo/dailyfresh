from django.db import models

class BaseModel(models.Model):
    '''
    abstract base class, 该抽象类 会为 所有子类：添加3个属性，create_time, update_time, is_delete
    '''
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(default=False, verbose_name='删除标记')

    class Meta:
        # 指明该类，是抽象模型类
        abstract = True
