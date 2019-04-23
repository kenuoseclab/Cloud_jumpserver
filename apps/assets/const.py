# -*- coding: utf-8 -*-
#

UPDATE_ASSETS_HARDWARE_TASKS = [
    {
        'name': "setup",
        'action': {
            'module': 'setup'
        }
    }
]

ADMIN_USER_CONN_CACHE_KEY = "ADMIN_USER_CONN_{}"
TEST_ADMIN_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
        }
    }
]

ASSET_ADMIN_CONN_CACHE_KEY = "ASSET_ADMIN_USER_CONN_{}"

SYSTEM_USER_CONN_CACHE_KEY = "SYSTEM_USER_CONN_{}"
TEST_SYSTEM_USER_CONN_TASKS = [
    {
        "name": "ping",
        "action": {
            "module": "ping",
        }
    }
]

TASK_OPTIONS = {
    'timeout': 10,
    'forks': 10,
}

CLOUD_INSTANCE_DATA = {
    'id': None,             # node_id
    'ip': None,             # ip
    'hostname': None,       # 主机名
    'protocol': None,       # 通信协议:ssh,rdp
    'port': None,           # 协议对应端口
    'platform': None,       # 平台:linux,windows,MacOS
    'domain': None,         # 网域
    'is_active': None,      # 是否激活
    'admin_user': None,     # 管理用户名
    'public_ip': None,      # 公网ip
    'number': None,         # 资产编号
    'vendor': None,         # 制造商
    'model': None,          # 主机型号
    'sn': None,             # 序列号
    'cpu_model': None,      # CPU型号
    'cpu_count': None,      # CPU数量
    'cpu_cores': None,      # CPU核数
    'cpu_vcpus': None,      # CPU频率
    'memory': None,         # 内存大小
    'disk_total': None,     # 硬盘大小
    'disk_info': None,      # 硬盘详情
    'os': None,             # 服务器系统 centos,ubuntu
    'os_version': None,     # 系统版本
    'os_arch': None,        # 系统架构
    'hostname_raw': None,   # 原主机域名
    'created_by': None,     # 创建者
    'comment': dict()       # 备注
}
