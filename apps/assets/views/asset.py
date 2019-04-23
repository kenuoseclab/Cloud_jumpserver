# coding:utf-8
from __future__ import absolute_import, unicode_literals

import csv
import json
import uuid
import codecs
import chardet
from io import StringIO

from django.db import transaction
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, FormView, UpdateView
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib.messages.views import SuccessMessageMixin

from common.mixins import JSONResponseMixin
from common.utils import get_object_or_none, get_logger
from common.permissions import AdminUserRequiredMixin
from common.const import create_success_msg, update_success_msg
from orgs.utils import current_org
from .. import forms
from ..models import Asset, AdminUser, SystemUser, Label, Node, Domain

__all__ = [
    'AssetListView', 'AssetCreateView', 'AssetUpdateView',
    'UserAssetListView', 'AssetBulkUpdateView', 'AssetDetailView',
    'AssetDeleteView', 'AssetExportView', 'BulkImportAssetView',
]
logger = get_logger(__file__)


class AssetListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/asset_list.html'

    def get_context_data(self, **kwargs):
        Node.root()
        context = {
            'app': _('Assets'),
            'action': _('Asset list'),
            'labels': Label.objects.all().order_by('name'),
            'nodes': Node.objects.all().order_by('-key'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserAssetListView(LoginRequiredMixin, TemplateView):
    template_name = 'assets/user_asset_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'action': _('My assets'),
            'system_users': SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = Asset
    form_class = forms.AssetCreateForm  # form表单
    template_name = 'assets/asset_create.html'  # 入口模板
    success_url = reverse_lazy('assets:asset-list')  # 成功后跳转页面

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        node_id = self.request.GET.get("node_id")
        if node_id:
            node = get_object_or_none(Node, id=node_id)
        else:
            node = Node.root()
        form["nodes"].initial = node
        return form

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create asset'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return create_success_msg % ({"name": cleaned_data["hostname"]})


class AssetBulkUpdateView(AdminUserRequiredMixin, ListView):
    model = Asset
    form_class = forms.AssetBulkUpdateForm
    template_name = 'assets/asset_bulk_update.html'
    success_url = reverse_lazy('assets:asset-list')
    success_message = _("Bulk update asset success")
    id_list = None
    form = None

    def get(self, request, *args, **kwargs):
        assets_id = self.request.GET.get('assets_id', '')
        self.id_list = [i for i in assets_id.split(',')]

        if kwargs.get('form'):
            self.form = kwargs['form']
        elif assets_id:
            self.form = self.form_class(
                initial={'assets': self.id_list}
            )
        else:
            self.form = self.form_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, self.success_message)
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Bulk update asset'),
            'form': self.form,
            'assets_selected': self.id_list,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AssetUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Asset
    form_class = forms.AssetUpdateForm
    template_name = 'assets/asset_update.html'
    success_url = reverse_lazy('assets:asset-list')

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update asset'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_message(self, cleaned_data):
        return update_success_msg % ({"name": cleaned_data["hostname"]})


class AssetDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Asset
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:asset-list')


class AssetDetailView(LoginRequiredMixin, DetailView):
    model = Asset
    context_object_name = 'asset'
    template_name = 'assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        nodes_remain = Node.objects.exclude(assets=self.object)
        context = {
            'app': _('Assets'),
            'action': _('Asset detail'),
            'nodes_remain': nodes_remain,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


# 资产导出
@method_decorator(csrf_exempt, name='dispatch')
class AssetExportView(LoginRequiredMixin, View):
    # get 方法用来下载导入csv资产列表
    def get(self, request):
        spm = request.GET.get('spm', '')
        assets_id_default = [Asset.objects.first().id] if Asset.objects.first() else []
        assets_id = cache.get(spm, assets_id_default)
        fields = [
            field for field in Asset._meta.fields
            if field.name not in [
                'date_created', 'org_id'
            ]
        ]
        filename = 'assets-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        assets = Asset.objects.filter(id__in=assets_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        writer.writerow(header)

        for asset in assets:
            data = [getattr(asset, field.name) for field in fields]
            writer.writerow(data)
        return response

    def post(self, request, *args, **kwargs):
        try:
            assets_id = json.loads(request.body).get('assets_id', [])
            node_id = json.loads(request.body).get('node_id', None)
        except ValueError:
            return HttpResponse('Json object not valid', status=400)

        if not assets_id:
            node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
            assets = node.get_all_assets()
            for asset in assets:
                assets_id.append(asset.id)

        spm = uuid.uuid4().hex
        cache.set(spm, assets_id, 300)
        url = reverse_lazy('assets:asset-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


# 模板导入资产
class BulkImportAssetView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = forms.FileForm

    def form_valid(self, form):
        node_id = self.request.GET.get("node_id")
        node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
        # 获取csv文件
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index

        # 读取csv文件
        file_data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(file_data)

        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]  # 逐行读取csv文件

        # 获取Asset数据表字段
        fields = [
            field for field in Asset._meta.fields
            if field.name not in [
                'date_created'
            ]
        ]
        # 获取csv表头
        header_ = csv_data[0]
        # 构造映射
        mapping_reverse = {field.verbose_name: field.name for field in fields}
        # 通过csv表头,结合asset数据表字段,获取存在的字段
        attr = [mapping_reverse.get(n, None) for n in header_]
        if None in attr:  # 判断字段是否缺少
            data = {'valid': False,
                    'msg': 'Must be same format as '
                           'template or export file'}
            return self.render_json_response(data)

        # 将插入的结果分为三个类型
        created, updated, failed = [], [], []
        assets = []

        for row in csv_data[1:]:  # 从csv第二行读取csv文件
            if set(row) == {''}:
                continue
            asset_dict_raw = dict(zip(attr, row))  # 构建插入数据库的原始数据--字典类型
            asset_dict = dict()

            for k, v in asset_dict_raw.items():  # k表示数据对应字段名,v为对应字段名
                v = v.strip()
                if k == 'is_active':
                    v = False if v in ['False', 0, 'false'] else True
                elif k == 'admin_user':
                    v = get_object_or_none(AdminUser, name=v)  # 查询AdminUser中查找admin_user字段是否存在数据库中,如果不存在则该字段值为none
                elif k in ['port', 'cpu_count', 'cpu_cores']:
                    try:
                        v = int(v)
                    except ValueError:
                        v = ''
                elif k == 'domain':
                    v = get_object_or_none(Domain, name=v)
                elif k == 'platform':
                    v = v.lower().capitalize()
                if v != '':
                    asset_dict[k] = v

            asset = None
            asset_id = asset_dict.pop('id', None)
            if asset_id:
                asset = get_object_or_none(Asset, id=asset_id)

            if not asset:
                try:
                    if len(Asset.objects.filter(hostname=asset_dict.get('hostname'))):
                        raise Exception(_('already exists'))
                    with transaction.atomic():
                        asset = Asset.objects.create(**asset_dict)
                        if node:
                            asset.nodes.set([node])
                        created.append(asset_dict['hostname'])
                        assets.append(asset)
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


# # 公有云导入资产信息
# class CloudImportAssetView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
#     form_class = forms.AssetAkSyncForm
#
#     def form_valid(self, form):
#         '''重写form_valid函数'''
#         # 获取node_id
#         node_id = self.request.GET.get("node_id")
#         node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
#         # 从表单获取id,key
#         try:
#             secret_id = form.cleaned_data['secret_id']
#             secret_key = form.cleaned_data["secret_key"]
#             cloud_name = form.cleaned_data["cloud_name"]
#         except Exception as e:
#             data = {'valid': False,
#                     'msg': "some error,reason {}".format(str(e))}
#             return self.render_to_response(data)
#
#         # 检查数据库是否存在ak信息
#
#         ak = get_object_or_none(AK, secret_id=secret_id)
#         if ak:
#             ak_id = ak.id
#         else:
#             with transaction.atomic():
#                 ak_dict = {"cloud_name": cloud_name, "secret_id": secret_id, "secret_key": secret_key}
#                 ak = AK.objects.create(**ak_dict)
#                 ak_id = ak.id
#
#         cloud_node = create_cloud_node(cloud_name, ak_id)  # 获取云资产对应的节点id
#
#         # 逻辑处理获取公有云实例
#         try:
#             instances = Instances(secret_id, secret_key, cloud_name)
#         except TimeoutError:
#             return self.render_to_response(
#                 {'valid': False,
#                  'msg': 'request time out!'}
#             )
#
#         created, updated, failed = [], [], []
#         assets = []
#
#         if instances:
#             for instance in instances:
#                 projectID =  get_projectId(cloud_name,instance)
#                 project_node_key = create_project_node(cloud_node,projectID)
#
#                 asset_dict = genernate_asset_dic(cloud_name, instance)
#                 asset = None
#                 asset_id = asset_dict.pop('id', None)  # 字典中获取id的值,如果不存在赋值为None
#                 if asset_id:
#                     asset = get_object_or_none(Asset, id=asset_id)
#
#                 # 根据资产id检查是否存在资产,如果资产没有id,再通过hostname检查
#                 if not asset:
#                     try:
#                         # 如果通过hostname从数据库中查到了资产,则无法再次添加添加
#                         if len(Asset.objects.filter(hostname=asset_dict.get('hostname'))):
#                             raise Exception(_('already exists'))
#                         # 如果hostname没有匹配的资产,则进行自动创建资产
#                         with transaction.atomic():
#                             asset = Asset.objects.create(**asset_dict)
#                             # 检查是否请求分配了节点
#                             if node:
#                                 asset.nodes.set([node])
#                             assign_asset_to_node(project_node_key, asset_dict["hostname"])
#                             created.append(asset_dict['hostname'])
#                             assets.append(created)
#                     except Exception as e:
#                         failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
#                 # 如果数据库中通过id可以查到资产,则进行资产详情更新
#                 else:
#                     for k, v in asset_dict.items():
#                         if v != '':
#                             setattr(asset, k, v)
#                     try:
#                         asset.save()
#                         updated.append(asset_dict['hostname'])
#                     except Exception as e:
#                         failed.append('%s: %s' % (asset_dict['hostname'], str(e)))
#
#             data = {
#                 'created': created,
#                 'created_info': 'Created {}'.format(len(created)),
#                 'updated': updated,
#                 'updated_info': 'Updated {}'.format(len(updated)),
#                 'failed': failed,
#                 'failed_info': 'Failed {}'.format(len(failed)),
#                 'valid': True,
#                 'msg': 'Created: {}. Updated: {}, Error: {}'.format(len(created), len(updated), len(failed))
#             }
#
#             return self.render_json_response(data)
#
#         else:
#             data = {'valid': False,
#                     'msg': 'no instance for this account'}
#             return self.render_json_response(data)
