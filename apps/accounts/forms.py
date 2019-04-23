# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.mixins import OrgModelForm

from .models import CloudAccount


logger = get_logger(__file__)
__all__ = ['AccountCreateForm','FileForm','AccountAssetSyncForm']


class AccountCreateForm(OrgModelForm):
    class Meta:
        model = CloudAccount
        fields = ['name', 'cloud_provider', 'accesskey_id', 'accesskey_secert', 'is_available', 'comment']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': _('Account Name')}),
            'accesskey_id': forms.TextInput(attrs={'placeholder': _('AccessKey ID')}),
            'accesskey_secert': forms.TextInput(attrs={'placeholder': _('AccessKey Secert')}),
        }


class FileForm(forms.Form):
    file = forms.FileField()


class AccountAssetSyncForm(forms.Form):

    account_id = forms.CharField(
        max_length=200,
        error_messages={
            "required": "不能为空",
            "invalid": "格式错误"
        })

    hostname_map = forms.CharField(
        required=True,
        error_messages={
            "invalid": "格式错误"
        }
    )