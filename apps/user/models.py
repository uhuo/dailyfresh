from django.db import models

from django.contrib.auth.models import AbstractUser
from db.base_model import BaseModel

#from django.conf import settings
#from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

# Create your models here.

class User(AbstractUser, BaseModel):
    '''
    User model
    '''
    # def generate_active_token(self):
    #     '''
    #     生成用户签名字符串
    #     '''
    #     serializer = Serializer(settings.SECRET_KEY, 3600)
    #     info = {'confirm': self.id}
    #     token = serializer.dumps(info)
    #     return token.decode()

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


class AddressManager(models.Manager):
    '''地址模型管理器类'''
    # 自定义 模型 管理器类：的 2种 应用场景
    # 1. 改变 查询的 结果集：all()
    # 2. 封装(操作 模型类 对应 数据表的)方法：增删改查
    def get_default_address(self, user):
        '''获取用户 默认收货地址'''
        # self.model: self对象的 模型类
        try:
            # address = self.model.objects.get(user=user, is_default=True) 可以简写 为 下面一行
            address = self.get(user=user, is_default=True)
        except self.model.DoesNotExist:  # 没有 默认收货地址
            address = None

        return address


class Address(BaseModel):
    '''
    Address model
    '''
    user = models.ForeignKey('User', on_delete=models.CASCADE, verbose_name='所属账户')
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=256, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, null=True, verbose_name='邮政编码')
    phone = models.CharField(max_length=11, verbose_name='联系电话')
    is_default = models.BooleanField(default=False, verbose_name='是否默认收货地址')

    # 自定义一个 模型管理器 实例
    objects = AddressManager()

    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name

































































