# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

COMMENT_DIC = {"PublicIpAddresses": None,
               "ZoneId": None
               }
COMMENT = _('PublicIpAddresses: {PublicIpAddresses}; ZoneId :{ZoneId}')
CLOUD_INSTANCE_DATA = {
    'id': None,
    'ip': None,
    'hostname': None,
    'protocol': None,
    'port': None,
    'platform': None,
    'domain': None,
    'is_active': None,
    'admin_user': None,
    'public_ip': None,
    'number': None,
    'vendor': None,
    'model': None,
    'sn': None,
    'cpu_model': None,
    'cpu_count': None,
    'cpu_cores': None,
    'cpu_vcpus': None,
    'memory': None,
    'disk_total': None,
    'disk_info': None,
    'os': None,
    'os_version': None,
    'os_arch': None,
    'hostname_raw': None,
    'created_by': None,
    'comment': None
}
