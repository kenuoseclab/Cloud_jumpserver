# ~*~ coding: utf-8 ~*~
import codecs
import csv
import json
import uuid

import chardet
from io import StringIO

from django import forms
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView, DeleteView, UpdateView, FormView
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.detail import DetailView

from common.const import create_success_msg, update_success_msg

from common.mixins import JSONResponseMixin
from common.utils import get_object_or_none, is_uuid, get_logger
from assets.signals import post_user_create
from ..forms import SystemUserForm
from ..models import SystemUser, Node, CommandFilter
from common.permissions import AdminUserRequiredMixin

logger = get_logger(__file__)

__all__ = [
    'SystemUserCreateView', 'SystemUserUpdateView',
    'SystemUserDetailView', 'SystemUserDeleteView',
    'SystemUserAssetView', 'SystemUserListView',
    'SystemUserImportView', 'SystemUserExportView',
]


class FileForm(forms.Form):
    file = forms.FileField()


class SystemUserImportView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = FileForm

    def form_invalid(self, form):
        # logger.info('systemUserImportView=================form invalid')
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
        # logger.info('form_valid================================')
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index
        data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        header_ = csv_data[0]
        fields = [
            SystemUser._meta.get_field(name)
            for name in [
                'id', 'name', 'username', '_password', 'protocol', 'login_mode',
                'priority', 'comment'
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
            user_dict = dict(zip(attr, row))
            id_ = user_dict.pop('id')
            for k, v in user_dict.items():
                user_dict[k] = v
            user = get_object_or_none(SystemUser, id=id_) if id_ and is_uuid(id_) else None
            if not user:
                try:
                    with transaction.atomic():
                        user = SystemUser.objects.create(**user_dict)
                        created.append(user_dict['username'])
                        post_user_create.send(self.__class__, user=user)
                except Exception as e:
                    failed.append('%s: %s' % (user_dict['username'], str(e)))
            else:
                for k, v in user_dict.items():
                        setattr(user, k, v)
                try:
                    user.save()
                    updated.append(user_dict['username'])
                except Exception as e:
                    failed.append('%s: %s' % (user_dict['username'], str(e)))

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


@method_decorator(csrf_exempt, name='dispatch')
class SystemUserExportView(View):
    def get(self, request):
        fields = [
            SystemUser._meta.get_field(name)
            for name in [
                'id', 'name', 'username', '_password', 'protocol', 'login_mode',
                'priority', 'comment'
            ]
        ]
        spm = request.GET.get('spm', '')
        users_id = cache.get(spm, [])
        filename = 'asset-system-users-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        users = SystemUser.objects.filter(id__in=users_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        writer.writerow(header)

        for user in users:
            data = [getattr(user, field.name) for field in fields]
            writer.writerow(data)

        return response

    def post(self, request):
        try:
            users_id = json.loads(request.body).get('users_id', [])
        except ValueError:
            return HttpResponse('Json object not valid', status=400)
        spm = uuid.uuid4().hex
        cache.set(spm, users_id, 300)
        url = reverse('assets:system-user-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class SystemUserListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/system_user_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_create.html'
    success_url = reverse_lazy('assets:system-user-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create system user'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = SystemUser
    form_class = SystemUserForm
    template_name = 'assets/system_user_update.html'
    success_url = reverse_lazy('assets:system-user-list')
    success_message = update_success_msg

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update system user')
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserDetailView(AdminUserRequiredMixin, DetailView):
    template_name = 'assets/system_user_detail.html'
    context_object_name = 'system_user'
    model = SystemUser

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('System user detail'),
            'cmd_filters_remain': CommandFilter.objects.exclude(system_users=self.object)
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SystemUserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = SystemUser
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:system-user-list')


class SystemUserAssetView(AdminUserRequiredMixin, DetailView):
    model = SystemUser
    template_name = 'assets/system_user_asset.html'
    context_object_name = 'system_user'

    def get_context_data(self, **kwargs):
        nodes_remain = sorted(Node.objects.exclude(systemuser=self.object), reverse=True)
        context = {
            'app': _('assets'),
            'action': _('System user asset'),
            'nodes_remain': nodes_remain
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)
