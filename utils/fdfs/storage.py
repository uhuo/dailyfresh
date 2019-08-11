from django.core.files.storage import Storage

from fdfs_client.client import *

from django.conf import settings

class FDFSStorage(Storage):
    '''fastdfs文件存储类'''
    def  __init__(self, client_conf=None, base_url=None):
        if client_conf == None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url == None:
            base_url = settings.FDFS_STORAGE_URL
        self.base_url = base_url


    def _open(self, name, mode='rb'):
        '''打开文件时 调用该函数'''
        # 用不到 打开文件，所以省略
        pass

    # 通过后台管理页面，选文件 并 上传时
    # django会调用_save方法(并给_save方法传递2个参数：name: 所要上传文件的名字，content: (包含文件内容的)File类的实例对象)
    def _save(self, name, content):
        '''保存文件时 调用该函数'''
        # name: 所要上传文件的名字
        # content: File类的实例(包含上传文件内容的File实例对象)
        # 返回值: fastdfs中 存储文件时 使用的文件名(被保存到 数据库的表 中)

        # 创建一个Fdfs_client对象
        # client = Fdfs_client('./utils/fdfs/client.conf')    #会根据./utils/fdfs/client.conf文件的配置，传给远端的tracker
        # trackers = get_tracker_conf('/Users/leesam/PycharmProjects/dailyfresh/utils/fdfs/client.conf')
        trackers = get_tracker_conf(self.client_conf)
        client = Fdfs_client(trackers)

        # 上传文件到 fastdfs文件系统 中
        # content.read() 可以从File的实例对象content中 读取 文件内容
        # upload_by_buffer返回内容为 字典。格式如下 注释部分
        res = client.upload_by_buffer(content.read()) # upload_by_buffer 根据文件内容 上传文件

        # dict {
        #
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        #
        # }

        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('upload file to fastdfs failed.')

        # 获取 返回的 文件id
        filename = res.get('Remote file_id')

        # 只能返回str类型, filename为bytes类型(需要转换类型，不然会报错)
        return filename.decode()

    # django在调用_save之前，会先调用_exists
    # _exists 根据 文件的name，判断 文件 是否存在于 文件系统中。存在：返回True，不存在：返回False
    def exists(self, name):
        '''django 判断 文件名 是否可用'''
        # 因为 文件是存储在 fastdfs文件系统中的，所以 对于django来说：不存在 文件名不可用 的情况
        # 因为 fastdfs是根据文件内容 得到文件名的(不存在文件名相同 文件内容不同，因而 无法存储的问题)
        return False

    def url(self, name):
        '''返回 访问文件name 所需的url路径'''
        # django调用url方法时，所传递的 name参数：数据库 表中所存的 文件名字符串(即是，fastdfs中存储文件时 使用的文件名)
        return self.base_url + name

















































