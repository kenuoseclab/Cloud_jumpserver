# -*- coding: utf-8 -*-
#
from django import forms
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.mixins import OrgModelForm

from ..models import Asset


logger = get_logger(__file__)
__all__ = ['AssetCreateForm', 'AssetUpdateForm', 'AssetBulkUpdateForm' ]


class AssetCreateForm(OrgModelForm):

    class Meta:

        model = Asset

        fields = [
            'hostname', 'ip', 'public_ip', 'port', 'comment',
            'nodes', 'is_active', 'labels', 'platform',
            'domain', 'protocol',
        ]

        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Nodes')
            }),
            # 'admin_user': forms.Select(attrs={
            #     'class': 'select2', 'data-placeholder': _('Admin user')
            # }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Label')
            }),
            'port': forms.TextInput(),
            'domain': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Domain')
            }),
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            # 'admin_user': _(
            #     'root or other NOPASSWD sudo privilege user existed in asset,'
            #     'If asset is windows or other set any one, more see admin user left menu'
            # ),
            'platform': _("Windows 2016 RDP protocol is different, If is window 2016, set it"),
            'domain': _("If your have some network not connect with each other, you can set domain")
        }


class AssetUpdateForm(OrgModelForm):
    class Meta:
        model = Asset
        fields = [
            'hostname', 'ip', 'port', 'nodes',  'is_active', 'platform',
            'public_ip', 'number', 'comment', 'labels',
            'domain', 'protocol',
        ]
        widgets = {
            'nodes': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Node')
            }),
            # 'admin_user': forms.Select(attrs={
            #     'class': 'select2', 'data-placeholder': _('Admin user')
            # }),
            'labels': forms.SelectMultiple(attrs={
                'class': 'select2', 'data-placeholder': _('Label')
            }),
            'port': forms.TextInput(),
            'domain': forms.Select(attrs={
                'class': 'select2', 'data-placeholder': _('Domain')
            }),
        }
        labels = {
            'nodes': _("Node"),
        }
        help_texts = {
            # 'admin_user': _(
            #     'root or other NOPASSWD sudo privilege user existed in asset,'
            #     'If asset is windows or other set any one, more see admin user left menu'
            # ),
            'platform': _("Windows 2016 RDP protocol is different, If is window 2016, set it"),
            'domain': _("If your have some network not connect with each other, you can set domain")
        }


class AssetBulkUpdateForm(OrgModelForm):
    assets = forms.ModelMultipleChoiceField(
        required=True,
        label=_('Select assets'), queryset=Asset.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                'class': 'select2',
                'data-placeholder': _('Select assets')
            }
        )
    )
    port = forms.IntegerField(
        label=_('Port'), required=False, min_value=1, max_value=65535,
    )

    # admin_user = forms.ModelChoiceField(
    #     required=False, queryset=AdminUser.objects,
    #     label=_("Admin user"),
    #     widget=forms.Select(
    #         attrs={
    #             'class': 'select2',
    #             'data-placeholder': _('Admin user')
    #         }
    #     )
    # )

    class Meta:
        model = Asset
        fields = [
            'assets', 'port', 'labels', 'nodes', 'platform'
        ]
        widgets = {
            'labels': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Label')}
            ),
            'nodes': forms.SelectMultiple(
                attrs={'class': 'select2', 'data-placeholder': _('Node')}
            ),
        }

    def save(self, commit=True):
        changed_fields = []
        for field in self._meta.fields:
            if self.data.get(field) not in [None, '']:
                changed_fields.append(field)

        cleaned_data = {k: v for k, v in self.cleaned_data.items()
                        if k in changed_fields}
        assets = cleaned_data.pop('assets')
        labels = cleaned_data.pop('labels', [])
        nodes = cleaned_data.pop('nodes', None)
        assets = Asset.objects.filter(id__in=[asset.id for asset in assets])
        assets.update(**cleaned_data)

        if labels:
            for asset in assets:
                asset.labels.set(labels)
        if nodes:
            for asset in assets:
                asset.nodes.set(nodes)
        return assets


# class AssetAkSyncForm(forms.Form):
#     cloud_name = forms.CharField(
#         label=_("Cloud_name"),
#         initial=2,
#         widget=forms.widgets.Select(choices=((1, "Ali"), (2, "Tencent"), (3, "HuaWei"), (4, "AWS"),))
#     )
#
#     secret_id = forms.CharField(
#         max_length=128,
#         required=True,
#         label=_("Secret_ID"),
#         error_messages={
#             "required": "不能为空",
#             "invalid": "格式错误"
#         })
#
#     secret_key = forms.CharField(
#         max_length=128,
#         required=True,
#         label=_("Secret_Key")
#     )

