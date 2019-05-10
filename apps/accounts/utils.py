# ~*~ coding: utf-8 ~*~

import binascii
import hashlib
import hmac
import sys
import urllib.parse
import urllib.request
import time
import random
import requests
import json
import threading

from django.db import transaction
from django.utils.translation import gettext as _

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkecs.request.v20140526.DescribeInstancesRequest import DescribeInstancesRequest
from aliyunsdkcore.acs_exception.exceptions import ServerException

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models

from common.utils import get_object_or_none
from assets.models import Asset, SystemUser, AdminUser, Node
from .const import CLOUD_INSTANCE_DATA, COMMENT_DIC, COMMENT

'''
data:20190315
auth:Failymao
connect cloud factory by ak,then get all
instances
'''


class TencentInstancesByAk:
    '''get instances by tencent ak '''

    instances = []

    def __init__(self, secret_id, secret_key):
        self.cred = credential.Credential(secret_id, secret_key)
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "cvm.tencentcloudapi.com"
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile

    @property
    def get_all_regions(self):
        try:
            client = cvm_client.CvmClient(self.cred, "", self.clientProfile)
            req = models.DescribeRegionsRequest()
            res = client.DescribeRegions(req)
            res = json.loads(res.to_json_string())
            regions = res.get("RegionSet")
            return regions
        except TencentCloudSDKException:
            return {"msg": _("InvalidAccessKeyId.NotFound Specified access key is not found")}


    def get_region_instance(self, region, offset_str=''):

        offset = "1" * len(offset_str)
        data = {"Offset": len(offset),
                "Limit": 100}
        try:
            client = cvm_client.CvmClient(self.cred, region, self.clientProfile)
            req = models.DescribeInstancesRequest()
            params = json.dumps(data)
            req.from_json_string(params)

            res = client.DescribeInstances(req)
            res = json.loads(res.to_json_string())
            tmp_ins = res.get("InstanceSet")
            for ins in tmp_ins:
                self.instances.append(ins)
            totalCount = res.get("TotalCount")

            if totalCount > data["Offset"] + data["Limit"]:
                offset_str = offset + "1" * len(tmp_ins)
                self.get_region_instance(region, offset_str=offset_str)
            else:
                return self.instances
        except TencentCloudSDKException:
            return {"msg": _("InvalidAccessKeyId.NotFound Specified access key is not found")}

    def get_all_instances(self):
        regions = self.get_all_regions
        if isinstance(regions, dict):
            return regions
        else:
            tasks = []
            for region in regions:
                t = threading.Thread(target=self.get_region_instance,args=(region["Region"],))
                tasks.append(t)

            for t in tasks:
                t.start()

            for t in tasks:
                if t.is_alive():
                    t.join()


class AliInstancesByAK:
    instances = []

    def __init__(self, secret_id, secret_key):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.request = CommonRequest()

    @property
    def __common_request_settings(self):
        request = self.request
        request.set_accept_format('json')
        request.set_method('POST')
        request.set_protocol_type('https')  # https | http
        request.set_version('2014-05-26')
        return request

    def get_region_instance_detail(self, region_id, instance_page=''):
        '''get instances from one special region
        :param region_id: a string,regionID,区域id ,egg:`cn-qingdao`
        :return: a list, all instances
        '''
        tmp_list = "1"* len(instance_page)
        client = AcsClient(self.secret_id, self.secret_key, region_id)
        request = DescribeInstancesRequest()
        request.set_accept_format('json')
        request.set_PageSize(100)

        try:
            response = client.do_action_with_exception(request)
            str_response = str(response, encoding="utf-8")
            result = json.loads(str_response).get('Instances').get('Instance')
            if result:
                totalCount = json.loads(str_response).get("TotalCount")
                page_number = json.loads(str_response).get("PageNumber")
                self.instances.append(result)
                len_list = tmp_list + "1" * len(result)
                if totalCount > len(len_list):
                    request.set_PageNumber(page_number + 1)
                    self.get_region_instance_detail(region_id, instance_page=len_list)
                else:
                    return
            else:
                return
        except Exception:
            return {"msg":_("Import asset occur error, pls try again later!") }

        
    @property
    def get_all_regions(self):
        '''get all available reigins for current region
        :return: a list, which is mapping for regions
        '''
        try:
            client = AcsClient(self.secret_id, self.secret_key, "default")
            request = self.__common_request_settings
            request.set_action_name('DescribeRegions')
            request.set_domain('ecs.aliyuncs.com')
            response = client.do_action_with_exception(request)
            str_response = (str(response, encoding='utf-8'))
            regions = json.loads(str_response).get('Regions').get('Region')
            return regions
        except ServerException:
            return {"msg":_("InvalidAccessKeyId.NotFound Specified access key is not found")}

    def get_all_instances(self):
        '''get instances through muti_threading
        :return:
        '''
        try:
            regions = self.get_all_regions
            if isinstance(regions,dict):
                return regions
            else:
                tasks = []
                for ins in regions:
                    t = threading.Thread(target=self.get_region_instance_detail,
                                         args=(ins["RegionId"],))
                    tasks.append(t)

                for t in tasks:
                    t.start()

                for t in tasks:
                    if t.is_alive():
                        t.join()
        except Exception:
            return {"msg":_("Import asset occur error, pls try again later!") }



class HuaweiInstancesByAk:
    '''HuaWei cloud instances object'''

    def __init__(self):
        pass

    def get_all_regions(self):
        pass

    def get_region_instance_detail(self):
        pass

    def get_all_instances(self):
        pass


def dezip_list(instance, result=None):
    '''解压处理嵌套列表'''
    if result is None:
        result = []
    for item in instance:
        if isinstance(item, list):
            dezip_list(item, result)
        else:
            result.append(item)
    return result


def Instances(secret_id, secret_key, cloud_name):
    ''' choice one cloud factory and input secret_key and secret_id,to get all instances
    :param secret_key: secret_key, a string.
    :param secret_id: secret_id, astring.
    :param cloud_name: Cloud server name,egg: Ali, Tencent,HuaWei, AWS...
    :return: a list of instances
    '''
    if cloud_name == "Aliyun":
        ali = AliInstancesByAK(secret_id, secret_key)
        err = ali.get_all_instances()
        if err:
            return err
        return dezip_list(ali.instances)

    elif cloud_name == "Qcloud":
        tec = TencentInstancesByAk(secret_id, secret_key)
        err = tec.get_all_instances()
        if err:
            return err
        return tec.instances
    elif cloud_name == "HuaWei":
        pass


def genernate_asset_dic(cloud_name, instance):
    '''generate asset dict format insert to Asset DB
    :param cloud_name: a string, cloud server factory.`Tencent,Ali,HuaWei,AWS`
    :param instance:a dict, instance of public cloud server
    :return:a dict,
    '''
    asset_dict = CLOUD_INSTANCE_DATA
    if instance:
        if cloud_name == "Qcloud":
            for k, v in instance.items():
                if k == "InstanceState":
                    asset_dict["is_active"] = True if v == "RUNNING" else False
                elif k == "PrivateIpAddresses":
                    asset_dict["ip"] = v[0]
                elif k == "Memory":
                    asset_dict["memory"] = v
                elif k == "OsName":
                    v_list = v.split(" ")
                    asset_dict["os"] = v_list[0]
                    asset_dict["os_version"] = " ".join(v_list[1:-1])
                    asset_dict["os_arch"] = v_list[-1]

                    if "window" in v.lower():
                        asset_dict["platform"] = "Windows"
                        asset_dict["protocol"] = "rdp"
                        asset_dict["port"] = 3389
                    else:
                        asset_dict["platform"] = "Linux"
                        asset_dict["protocol"] = "ssh"
                        asset_dict["port"] = 22
                elif k == "InstanceName":
                    asset_dict["hostname"] = v
                elif k == "Memory":
                    asset_dict["memory"] = '{:.1f}G'.format(v)
                elif k == "CPU":
                    asset_dict["cpu_count"] = 1
                    asset_dict["cpu_cores"] = v
                elif k == "SystemDisk":
                    asset_dict["disk_total"] = '{:.1f}G'.format(v["DiskSize"])
                    asset_dict["disk_info"] = str({v["DiskType"]: v["DiskSize"]})
                elif k == "InstanceId":
                    asset_dict["number"] = v

                elif k == "PublicIpAddresses":
                    if isinstance(v, list):
                        COMMENT_DIC["PublicIpAddresses"] = v[0]
                        COMMENT_DIC[k] = v[0]
                    else:
                        COMMENT_DIC[k] = v
                elif k == "Placement":
                    COMMENT_DIC["ZoneId"] = v.get("Zone")

        elif cloud_name == "Aliyun":
            for k, v in instance.items():
                if k == "Status":
                    asset_dict["is_active"] = True if v == "Running" else False
                elif k == "VpcAttributes":
                    try:
                        asset_dict["ip"] = v.get("PrivateIpAddress").get("IpAddress")[0]
                    except IndexError:
                        asset_dict["ip"] = ''
                elif k == "Memory":
                    asset_dict["memory"] = "{:.1f}G".format(v / 1024)
                elif k == "OSType":
                    if "window" in v.lower():
                        asset_dict["platform"] = "Windows"
                        asset_dict["protocol"] = "rdp"
                        asset_dict["port"] = 3389
                    else:
                        asset_dict["platform"] = "Linux"
                        asset_dict["protocol"] = "ssh"
                        asset_dict["port"] = 22
                elif k == "OSName":
                    v_list = v.split(" ")
                    asset_dict["os"] = v_list[0]
                    asset_dict["os_version"] = " ".join(v_list[1:-1])
                    asset_dict["os_arch"] = v_list[-1]
                elif k == "InstanceName":
                    asset_dict["hostname"] = v
                elif k.lower() == "cpu":
                    asset_dict["cpu_count"] = 1
                    asset_dict["cpu_cores"] = v
                elif k == "InstanceId":
                    asset_dict["number"] = v

                elif k ==  "ZoneId":
                    COMMENT_DIC[k] = v if v else None
                elif k == "PublicIpAddress":
                    COMMENT_DIC["PublicIpAddresses"] = v.get("IpAddress")[0] if v.get("IpAddress") else None

        elif cloud_name == "HuaWei":
            pass
        else:  # AWS cloud
            pass
       
        asset_dict["comment"] = COMMENT.format(**COMMENT_DIC)
        
        return asset_dict
    else:
        return None


def create_cloud_node(account_provider, ak_id, account_name):
    ''' Create new node under the root Node.
    :param account_provider: a string, node value.
    :param account_name,a string. sub_name for node value,exp: node_value=ak.name
    :param ak_id, a string, according to account id.
    :return: a string. node_id
    '''
    try:
        node = get_object_or_none(Node, id=ak_id)
        if node:
            cloud_node = node
            return cloud_node
        else:
            full_node_value = account_provider + " " + account_name
            node_by_value = get_object_or_none(Node, value=full_node_value)
            if node_by_value:
                return node_by_value
            else:
                child_sub_key = 0
                while True:
                    key = '1:{}'.format(child_sub_key)
                    child_node = get_object_or_none(Node, key=key)
                    if child_node:
                        child_sub_key += 1
                    else:
                        with transaction.atomic():
                            node_dic = {"value": full_node_value, "key": key, "id": ak_id}
                            child_node = Node.objects.create(**node_dic)
                            break
                return child_node
    except Exception:
        return None


def create_project_node(cloud_node, projectID=0):
    '''create new project node by cloud_no and project id in instance.
    :param cloud_node:a db object,cloud node
    :param projectID:a int, project id in instance
    :return:a string new project node id
    '''
    node = get_object_or_none(Node, key=cloud_node.key)
    if node:
        key = node.key
        value =_("Default Node") if projectID == 0 else "ProjectID {ProjectID}".format(**{"ProjectID":projectID})
        project_node_key = key + ":{}".format(projectID)
        project_node = get_object_or_none(Node, key=project_node_key)
        if project_node:
            return project_node.key
        else:
            with transaction.atomic():
                node_dic = {"value": _(value), "key": project_node_key}
                project_node = Node.objects.create(**node_dic)
                project_node_key = project_node.key
                return project_node_key


def get_projectId(cloud_name, instance):
    '''get project ID from instance
    :param cloud_name: a string, cloud name
    :param instance:  a mapping, instance
    :return: a int, project id
    '''
    if instance:
        if cloud_name == "Qcloud":
            return instance.get("Placement").get("ProjectId")
        elif cloud_name == "Aliyun":
            projectID = instance.get("ResourceGroupId")
            if projectID:
                return projectID
            else:
                return 0
        elif cloud_name == "HuaWei":
            pass
        elif cloud_name == "AWS":
            pass
        else:
            pass


def assign_asset_to_node(key, hostname):
    '''assign new asset to special node
    :param key: a string, node  id
    :param hostname: a string, asset of hostname
    :return: a  bool.
    '''
    node = get_object_or_none(Node, key=key)
    asset = get_object_or_none(Asset, hostname=hostname)
    try:
        if node and asset:
            asset.nodes.add(node)
    except Exception:
        return "assgin to node occur error"
        
       


if __name__ == "__main__":
    secretId = "AKIDZyGQXbErpY*************"
    secretKey = "kFUTDk38yZw4xc5JHzRdZFfs"
    cloud_name = "Qcloud"
    print(Instances(secretId, secretKey, cloud_name))
