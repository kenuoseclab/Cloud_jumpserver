# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.urls import path
from rest_framework_bulk.routes import BulkRouter
from .. import api

app_name = 'accounts'

router = BulkRouter()
router.register(r'accounts', api.AccountViewSet, 'account') #accounts-api:account



urlpatterns = [
    path('account/<uuid:pk>/assets/', api.AccountAssetsApi.as_view(), name='account-assets'),
]
urlpatterns += router.urls