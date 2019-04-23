#-*-coding:utf-8-*-

from rest_framework_bulk import BulkModelViewSet
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from common.permissions import IsOrgAdmin, IsCurrentUserOrReadOnly, IsOrgAdminOrAppUser
from common.mixins import IDInFilterMixin
from common.utils import get_logger, get_object_or_none

from .. import serializers
from ..models import CloudAccount
from ..utils import Instances

logger = get_logger(__name__)
__all__ = [
    "AccountViewSet", "AccountAssetsApi"
]


class AccountViewSet(IDInFilterMixin, BulkModelViewSet):
    filter_fields = ("id", "name")
    search_fields = filter_fields
    ordering_fields = ("name", "cloud_provider", "last_sync_time")
    queryset = CloudAccount.objects.all()
    serializer_class = serializers.AccountSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsOrgAdminOrAppUser,)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset().distinct()
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset


class AccountAssetsApi(APIView):
    """
    Get instances by cloud account  API
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AccountAssetSerializer

    def post(self, request, **kwargs):
        uuid = str(kwargs.get('pk'))                                        # parse pk  value from url
        serializer = serializers.AccountAssetSerializer(data=request.data)  # serializr the parameters from request data
        IsRightSerialied = serializer.is_valid()
        if IsRightSerialied:
            data = serializer.data
            account_name = data.get("name")                                  # get the account name through request data
            account_id = "".join(uuid.split("-"))
            ak = get_object_or_none(CloudAccount, id=account_id)             # check account info from db
            if not ak:
                ak = get_object_or_none(CloudAccount, name=account_name)
                if not ak:
                    res = {"msg":_("Not have account info,check name or uuid")}
                    return Response(res, status=status.HTTP_404_NOT_FOUND)
                account_id = ak.id
            if not cache.has_key(account_id):
                cloud_provider = ak.cloud_provider
                secret_key = ak.accesskey_secert
                secret_id = ak.accesskey_id
                ins = Instances(secret_id, secret_key, cloud_provider)                         # get all instances by ak account
                if isinstance(ins,dict):
                    return Response(ins,status=status.HTTP_417_EXPECTATION_FAILED)
                cache.set(account_id, ins, 60 * 30)
            ins = cache.get(account_id)
            if ins:
                res_obj = []
                for i in ins:
                    response_data = dict()
                    response_data["hostname"] = i.get("InstanceName")
                    IP = i.get("PrivateIpAddresses")                                          # tencent
                    if not IP:
                        IP = i.get("VpcAttributes").get("PrivateIpAddress").get("IpAddress")  # ali
                    response_data["ip"] = "".join(IP)
                    activate = i.get("Status")
                    response_data["connectivity"] = False if activate == "Stopped" else True  # instance status
                    res_obj.append(response_data)
                return Response(res_obj, status=status.HTTP_201_CREATED)
            return Response({"msg": _("No instance for this account!")}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
