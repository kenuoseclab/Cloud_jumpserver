# coding: utf-8

from __future__ import unicode_literals

import uuid

from django.utils.translation import ugettext_lazy as _
from django.db import models
from orgs.mixins import OrgModelMixin


__all__ = ['CloudAccount']


class CloudAccount(OrgModelMixin):
    CLOUND_ALI = "Aliyun"
    CLOUND_TENCENT = "Qcloud"
    CLOUD_HUAWEI = "HuaWei"
    CLOUND_Amazon = "AWS"

    CLOUD_PROVIDWE = (
        (CLOUND_ALI, _('Aliyun')),
        (CLOUND_TENCENT, _('Qcloud')),
        # (CLOUD_HUAWEI, _('HuaWei')),
        # (CLOUND_Amazon,_('AWS')),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=100, verbose_name=_('Account Name'))
    cloud_provider = models.CharField(max_length=50, choices=CLOUD_PROVIDWE, default='', verbose_name=_('Cloud Provider'))
    accesskey_id = models.CharField(max_length=200, verbose_name=_('AccessKey ID'))
    accesskey_secert = models.CharField(max_length=200, verbose_name=_('AccessKey Secert'))
    is_available = models.BooleanField(default=1, verbose_name=_('Is Available'))
    last_sync_time = models.DateTimeField(null=True, blank=True, verbose_name=_('Last sync time'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @property
    def cloud_provider_display(self):
        return self.get_cloud_provider_display()

    class Meta:
        verbose_name = _("Cloud Accounts")
