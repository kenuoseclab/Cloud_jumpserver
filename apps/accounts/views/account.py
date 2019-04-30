# coding:utf-8
from __future__ import absolute_import, unicode_literals

import datetime
import codecs
import csv
import json
import uuid
from io import StringIO
import chardet

from django.db import transaction
from django.urls import reverse_lazy, reverse
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import (
    CreateView, DeleteView, UpdateView, FormView
)

from django.contrib.messages.views import SuccessMessageMixin

from ..models import CloudAccount
from ..signals import post_user_create
from ..forms import AccountCreateForm, FileForm, AccountAssetSyncForm
from ..utils import (genernate_asset_dic, create_cloud_node,
                     create_project_node, get_projectId, assign_asset_to_node)
from common.const import create_success_msg, update_success_msg
from common.utils import get_logger, is_uuid, get_object_or_none
from common.permissions import AdminUserRequiredMixin
from common.mixins import JSONResponseMixin
from assets.models import Asset, Node

__all__ = [
    'AccountListView', 'AccountCreateView', 'AccountDetailView',
    'AccountUpdateView', 'AccountDeleteView', 'AccountExportView',
    'AccountimportView', 'AccountAssetImportView',
]

logger = get_logger(__file__)


class AccountListView(AdminUserRequiredMixin, TemplateView):
    model = CloudAccount
    # context_object_name = 'cloud_account'
    template_name = 'accounts/account_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _('Cloud Accounts'),
            'action': _('Accounts list'),
        })
        return context


class AccountCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = CloudAccount
    form_class = AccountCreateForm
    template_name = 'accounts/account_create.html'
    success_url = reverse_lazy('accounts:account-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'app': _('Cloud Accounts'), 'action': _('Create cloud account')})
        return context


class AccountDetailView(AdminUserRequiredMixin, DetailView):
    model = CloudAccount
    template_name = 'accounts/account_detail.html'

    # context_object_name = "cloud_account"

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Cloud Accounts'),
            'action': _('Cloud accounts detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AccountUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CloudAccount
    form_class = AccountCreateForm
    template_name = 'accounts/account_create.html'
    success_url = reverse_lazy('accounts:account-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Cloud Accounts'),
            'action': _('Update Cloud Accounts'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return update_success_msg % ({"name": cleaned_data["name"]})


class AccountDeleteView(AdminUserRequiredMixin, DeleteView):
    model = CloudAccount
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('accounts:account-list')


@method_decorator(csrf_exempt, name='dispatch')
class AccountExportView(View):
    def get(self, request):
        fields = [
            CloudAccount._meta.get_field(name)
            for name in [
                'id', 'name', 'cloud_provider', 'accesskey_id', 'accesskey_secert',
            ]
        ]
        spm = request.GET.get('spm', '')
        accounts_id = cache.get(spm, [])
        filename = 'cloud_account-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        accounts = CloudAccount.objects.filter(id__in=accounts_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        writer.writerow(header)

        for account in accounts:
            data = [getattr(account, field.name) for field in fields]
            writer.writerow(data)

        return response

    def post(self, request):
        try:
            accounts_id = json.loads(request.body).get('accounts_id', [])
        except ValueError:
            return HttpResponse('Json object not valid', status=400)
        spm = uuid.uuid4().hex
        cache.set(spm, accounts_id, 300)
        url = reverse('accounts:account-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class AccountimportView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = FileForm

    def form_invalid(self, form):
        try:
            error = form.errors.values()[-1][-1]
        except Exception as e:
            error = _('Invalid file.')
        data = {
            'success': False,
            'msg': error
        }
        return self.render_json_response(data)

    # todo: need be patch, method to long
    def form_valid(self, form):
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index
        data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        header_ = csv_data[0]
        fields = [
            CloudAccount._meta.get_field(name)
            for name in [
                'id', 'name', 'cloud_provider', 'accesskey_id', 'accesskey_secert',
            ]
        ]
        mapping_reverse = {field.verbose_name: field.name for field in fields}
        attr = [mapping_reverse.get(n, None) for n in header_]
        if None in attr:
            data = {'valid': False,
                    'msg': 'Must be same format as '
                           'template or export file'}
            return self.render_json_response(data)

        created, updated, failed = [], [], []
        for row in csv_data[1:]:
            if set(row) == {''}:
                continue
            account_dict = dict(zip(attr, row))
            id_ = account_dict.pop('id')
            for k, v in account_dict.items():
                account_dict[k] = v
            account = get_object_or_none(CloudAccount, id=id_) if id_ and is_uuid(id_) else None
            if not account:
                try:
                    with transaction.atomic():
                        account = CloudAccount.objects.create(**account_dict)
                        created.append(account_dict['name'])
                        post_user_create.send(self.__class__, account=account)
                except Exception as e:
                    failed.append('%s: %s' % (account_dict['name'], str(e)))
            else:
                for k, v in account_dict.items():
                    if v:
                        setattr(account, k, v)
                try:
                    account.save()
                    updated.append(account_dict['name'])
                except Exception as e:
                    failed.append('%s: %s' % (account['name'], str(e)))

        data = {
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'valid': True,
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)


class AccountAssetImportView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = AccountAssetSyncForm

    def form_valid(self, form):
        sync_time = datetime.datetime.now()
        account_id = self.request.GET.get("account_id")

        # Will create ROOT node while user first time importing assets.
        if not get_object_or_none(Node, key="1"):
            Node.root()

        try:
            account_id = account_id if account_id else form.cleaned_data['account_id']
            account_id = ''.join(account_id.split("-"))
            hostname_map = json.loads(form.cleaned_data["hostname_map"])

            if not hostname_map:
                data = {'valid': False, 'msg': _('Did not selected any assets')}
                return self.render_to_response(data)
        except Exception as e:
            data = {'valid': False,
                    'msg': _("some error,reason {error}".format(**{"error":str(e)}))}
            return self.render_to_response(data)

        ak = get_object_or_none(CloudAccount, id=account_id)
        if ak is None:
            pass

        ak.last_sync_time = sync_time
        ak.save()

        account_name = ak.name
        cloud_name = ak.cloud_provider
        cloud_node = create_cloud_node(cloud_name, account_id,account_name)

        created, updated, failed = [], [], []
        instances = cache.get(account_id, [])
        if instances:
            for instance in instances:
                for res_ins in hostname_map:
                    if res_ins["number"] == instance["InstanceId"]:
                        projectID = get_projectId(cloud_name, instance)
                        project_node_key = create_project_node(cloud_node, projectID)

                        asset_dict = genernate_asset_dic(cloud_name, instance)
                        asset = None
                        asset_id = asset_dict.pop('id', None)
                        if asset_id:
                            asset = get_object_or_none(Asset, id=asset_id)

                        if not asset:
                            try:
                                if len(Asset.objects.filter(number=asset_dict.get('number'))):
                                    raise Exception(_('already exists'))
                                with transaction.atomic():
                                    asset = Asset.objects.create(**asset_dict)
                                    assign_asset_to_node(project_node_key, asset_dict["hostname"])
                                    created.append(asset_dict['hostname'])
                            except Exception as e:
                                failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
                        else:
                            for k, v in asset_dict.items():
                                if v != '':
                                    setattr(asset, k, v)
                            try:
                                asset.save()
                                updated.append(asset_dict['hostname'])
                            except Exception as e:
                                failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
                    else:
                        continue

            data = {
                'created': created,
                'created_info': 'Created {}'.format(len(created)),
                'updated': updated,
                'updated_info': 'Updated {}'.format(len(updated)),
                'failed': failed,
                'failed_info': 'Failed {}'.format(len(failed)),
                'valid': True,
                'msg': 'Created: {}. Updated: {}, Error: {}'.format(len(created), len(updated), len(failed))
            }

            return self.render_json_response(data)

        else:
            data = {'valid': False,
                    'msg': _('No instance for this account')}
            return self.render_json_response(data)