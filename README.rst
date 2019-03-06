项目骨架
--------

说明如下(需要更新)：

::

    .
    ├── apps                             // 管理后台目录,也是各apps 所在目录
    │   ├── assets                       // 资产管理app(应用)
    │   │   ├── api                      // Restful api 逻辑代码,views模块对应
    │   │   ├── forms                    // form表单模块
    │   │   ├── migrations               // Models Migrations 版本控制目录 
    │   │   ├── models                   // ORM 数据库模块
    │   │   ├── serializers              // 将请求或数据库对象序列化python可读对象
    │   │   ├── templates                // 模板文件,使用层级模板,防止重名
    │   │   ├── templatetags             // 模板标签目录
    │   │   ├── urls                     // 视图函数与路由映射,包含api url 
    │   │   └── views                    // 视图函数模块
    │   │   ├── apps.py                  // 新版本 Django APP 设置文件,定义app命名
    │   │   ├── const.py                 // 常量配置文件
    │   │   ├── hands.py                 // 与其他app存在交互的模块相互调用               
    │   │   ├── tests.py                 // 测试用例文件
    │   │   ├── utils.py                 // 该app下的通用的函数方法
    │   │   ├── __init__.py              // 对外暴露的接口,放到该文件中,方便别的 APP 引用
    │   ├── audits                       // 日志审计app
    │   ├── authentication               // 用户认证模块(安全组件)
    │   ├── common                       // 系统设置app(email发送,terminal终端操作,设置) 
    │   ├── fixtures                     // 初始化数据目录
    │   │   ├── fake.json                // 生成大量测试数据    
    │   │   └── init.json                // 初始化项目数据库
    │   ├── jumpserver                   // 项目设置app
    │   │   ├── conf.py                  // 加载配置文件 
    │   │   ├── context_processor.py 
    │   │   ├── __init__.py
    │   │   ├── middleware.py            // 中间件文件
    │   │   ├── settings.py              // 项目设置文件
    │   │   ├── swagger.py
    │   │   ├── urls.py                  // 项目入口 Url(顶层url)
    │   │   ├── utils.py              
    │   │   ├── views.py                 // 视图函数
    │   │   └── wsgi.py                  // django框架WSGI服务器
    │   ├── locale                       // 项目多语言目录
    │   │   └── zh    
    │   ├── __init__.py                  // apps对外暴露接口
    │   ├── manage.py                    // 管理项目脚本文件
    │   ├── ops                          // 作业中心app(命令行)
    │   ├── orgs
    │   ├── perms                        // 权限管理 app
    │   ├── static                       // 顶层 静态文件
    │   ├── templates                    // 顶层templates
    │   ├── terminal                     // 是按web terminal app 
    │   └── users                        // 用户管理 app
    ├── build.sh                         // 自动构建脚本
    ├── config_example.yml               // 配置文件样例
    ├── config.yml                       // 生产环境配置文件
    ├── data                             
    │   ├── celery
    │   ├── media
    │   └── static
    ├── Dockerfile                       // docker 安装文件
    ├── docs                             // 所有 DOC 文件放到该目录
    ├── entrypoint.sh
    ├── jms							     // 启动脚本
    ├── LICENSE
    ├── logs                             // 日志目录
    ├── README.md                        // README 文档
    ├── requirements                     // 各系统依赖包
    │   ├── mac_requirements.txt
    │   ├── requirements.txt
    │   └── rpm_requirements.txt
    ├── run_server.py                     // 启动文件
    ├── tmp                               // 进程文件
    │   ├── beat.pid
    │   ├── celery.pid
    │   └── gunicorn.pid
    └── utils                             // 通用函数
