# coding: utf-8
from __future__ import unicode_literals

from django.urls import path
from .. import views

__all__ = ["urlpatterns"]

app_name = "accounts"

urlpatterns = [
    path('account/', views.AccountListView.as_view(), name='account-list'),
    path('account/create/', views.AccountCreateView.as_view(), name='account-create'),
    path('account/<uuid:pk>/', views.AccountDetailView.as_view(), name='account-detail'),
    path('account/<uuid:pk>/update/', views.AccountUpdateView.as_view(), name='account-update'),
    path('account/<uuid:pk>/delete/', views.AccountDeleteView.as_view(), name='account-delete'),
    path('account/export/', views.AccountExportView.as_view(), name='account-export'),
    path('account/import/', views.AccountimportView.as_view(), name='account-import'),
    path('account/<uuid:pk>/asset/import/', views.AccountAssetImportView.as_view(), name='account-asset-import'),

]
