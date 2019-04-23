# -*-coding:utf-8-*-
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from orgs.mixins import OrgModelMixin

__all__ = ['AK']


class AK(OrgModelMixin):
    CLOUND_ALI = "Ali"
    CLOUND_TENCENT = "Tencent"
    CLOUD_HUAWEI = "HuaWei"
    CLOUND_Amazon = "AWS"

    CLOUD_CHOICES = (
        (CLOUND_ALI, _("Ali")),
        (CLOUND_TENCENT, _("Tencent")),
        (CLOUD_HUAWEI, _("Tencent")),
        (CLOUND_Amazon, _("AWS"))
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    cloud_name = models.CharField(max_length=32, choices=CLOUD_CHOICES, default=CLOUND_TENCENT,verbose_name=_("cloud_name"))
    secret_id = models.CharField(max_length=128, verbose_name=_("secret_id"))
    secret_key = models.CharField(max_length=128, verbose_name=_("secret_key"))

    @classmethod
    def get_queryset_group_by_name(cls):
        names = cls.objects.values_list('cloud_name', flat=True)
        for name in names:
            yield name, cls.objects.filter(name=name)

    def __str__(self):
        return "id:{}\nkey:{}".format(self.secret_id, self.secret_key)

    class Meta:
        verbose_name = _("AK")
