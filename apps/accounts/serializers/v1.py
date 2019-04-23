#-*-coding:utf-8-*-

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer

from common.mixins import BulkSerializerMixin
from ..models import CloudAccount


class AccountSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CloudAccount
        list_serializer_class = BulkListSerializer
        fields = ['id', 'name', 'cloud_provider_display', 'accesskey_id', 'is_available', 'last_sync_time', ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related().select_related()
        return queryset

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        return fields


class AccountAssetSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=320, required=False)
    name = serializers.CharField(max_length=100, required=False)
    accesskey_id = serializers.CharField(max_length=200, required=False)


if __name__ == "__main__":
    project = {"id": "ax1230a2c3a", "accesskey_id": "123bac5621", "accesskey_secert": "a12b30981avx"}
    ser = AccountAssetSerializer(project)
    ser.data
