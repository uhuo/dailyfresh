from django.contrib.auth.decorators import login_required

    ################################################################################################
    ###### 访问一个地址时：如果 用户未登录(session中没有该用户信息)，
    ###### login_required会(根据配置LOGIN_URL = '/user/login/') 跳转到 登陆页面。
    ###### 并且 在登陆页面的地址后 添加next参数。next参数 是 之前访问的地址 的 路径
    ###### 如果 用户已经登陆(session中 有该用户信息)，执行login_required包裹的 视图view
    ######
    ###### 这样写(login_required(UserInfoView.as_view()))显得有些啰嗦,
    ###### 将login_required(as_view)封装在LoginRequiredMixin中,
    ###### 并让UserInfoView, UserOrderView, AddressView等 需要登录才能访问的页面，继承LoginRequiredMixin
    ###### (LoginRequiredMixin要在 子类的继承顺序 的 第一位)

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        # 调用父类的as_view
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)


