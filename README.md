# dailyfresh


django简易购物网站小项目-201908111636upload

	项目总结
	•	生鲜类产品  B2C  PC电脑端网页
	
	•	功能模块：用户模块  商品模块（首页、 搜索、商品） 购物车模块  订单模块（下单、 支付）
	
	•	用户模块：注册、登录、激活、退出、个人中心、地址
	
	•	商品模块：首页、详情、列表、搜索（haystack+whoosh）
	
	•	购物车： 增加、删除、修改、查询
	
	•	订单模块：确认订单页面、提交订单（下单）、请求支付、查询支付结果、评论
	
	•	django默认的认证系统 AbstractUser
	
	•	itsdangerous  生成签名的token （序列化工具 dumps  loads）
	
	•	邮件 （django提供邮件支持 配置参数  send_mail）
	
	•	 celery (重点  整体认识 异步任务)
	
	•	 页面静态化 （缓解压力  celery  nginx）
	
	•	 缓存（缓解压力， 保存的位置、有效期、与数据库的一致性问题）
	
	•	 FastDFS (分布式的图片存储服务， 修改了django的默认文件存储系统)
	
	•	 搜索（ whoosh  索引  分词）
	
	•	 购物车redis 哈希 历史记录redis list
	
	•	 ajax 前端用ajax请求后端接口
	
	•	 事务
	
	•	 高并发的库存问题 （悲观锁、乐观锁）
	
	•	 支付的使用流程
	
	•	 nginx （负载均衡  提供静态文件）
	
**项目架构图	**
![framework.png](https://upload-images.jianshu.io/upload_images/6174636-d9d70d6f7b7b3e8c.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

**项目部署图**
![deploy.png](https://upload-images.jianshu.io/upload_images/6174636-9a83af19d21958f7.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

**数据库设计图**
![DBtables.png](https://upload-images.jianshu.io/upload_images/6174636-c40e050bfc329e18.png?imageMogr2/auto-orient/strip%7CimageView2/2/w/1240)

