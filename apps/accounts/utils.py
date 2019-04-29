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
from aliyunsdkcore.acs_exception.exceptions import ServerException

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

    def __init__(self, secret_id, secret_key):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.timeData = str(int(time.time()))
        self.nonceData = int(random.random() * 10000)
        # self.actionData = action                        # Action一般是操作名称
        self.httpProfile = "cvm.tencentcloudapi.com"  # HOST
        self.signMethod = "HmacSHA256"  # 加密方法
        self.requestMethod = "GET"  # 请求方法，在签名时会遇到，如果签名时使用的是GET，那么在请求时也请使用GET
        self.versionData = '2017-03-12'  # 版本选择

    def sign(self, secretKey, signStr, signMethod):
        ''' 签名函数,参考api签名鉴权
        :param secretKey: 用户的secretKey
        :param signStr:   传递进来字符串，加密时需要使用
        :param signMethod: 加密方法
        :return: base64 编码后的签签名
        '''
        if sys.version_info[0] > 2:
            signStr = signStr.encode("utf-8")
            secretKey = secretKey.encode("utf-8")

        # 根据参数中的signMethod来选择加密方式
        if signMethod == 'HmacSHA256':
            digestmod = hashlib.sha256
        elif signMethod == 'HmacSHA1':
            digestmod = hashlib.sha1

        # 完成加密，生成加密后的数据
        hashed = hmac.new(secretKey, signStr, digestmod)
        base64 = binascii.b2a_base64(hashed.digest())[:-1]

        if sys.version_info[0] > 2:
            base64 = base64.decode()

        return base64

    def dictToStr(self, dictData):
        '''将Dict转为List并且拼接成字符串
        :param dictData: 请求参数,字典格式
        :return: 拼接好的字符串
        '''
        tempList = []
        for eveKey, eveValue in dictData.items():
            tempList.append(str(eveKey) + "=" + str(eveValue))
        return "&".join(tempList)

    def signStrFun(self, dictData):
        '''对字典进行排序
        :param dictData: 请求参数字典格式
        :return:
        '''
        tempList = []
        resultList = []
        tempDict = {}
        for eveKey, eveValue in dictData.items():
            tempLowerData = eveKey.lower()
            tempList.append(tempLowerData)
            tempDict[tempLowerData] = eveKey
        tempList.sort()
        for eveData in tempList:
            tempStr = str(tempDict[eveData]) + "=" + \
                      str(dictData[tempDict[eveData]])
            resultList.append(tempStr)
        return "&".join(resultList)

    def generate_sign_dic(self, **kwargs):
        '''生成签名字典函数,新加入Signature键
        :return:
        '''
        signDictData = {
            'Action': kwargs.get("action"),
            'Nonce': self.nonceData,
            'Region': kwargs.get('regionData'),
            'SecretId': self.secret_id,
            'SignatureMethod': self.signMethod,
            'Timestamp': int(self.timeData),
            'Version': self.versionData,
        }
        requestStr = "%s%s%s%s%s" % (
            self.requestMethod, self.httpProfile, "/", "?", self.signStrFun(signDictData))
        signData = urllib.parse.quote(self.sign(self.secret_key, requestStr, self.signMethod))
        actionArgs = signDictData
        actionArgs["Signature"] = signData
        return signDictData

    def generate_req_url(self, action='DescribeInstances', region_area=''):
        '''生成请求地址
        :return:
        '''
        actionArgs = self.generate_sign_dic(action=action, regionData=region_area)
        # 根据uri构建请求的url
        requestUrl = "https://%s/?" % (self.httpProfile)
        # 将请求的url和参数进行拼接
        req_url = requestUrl + self.dictToStr(actionArgs)
        return req_url

    def json_to_dict(self, str):
        import json
        dic = json.loads(str)
        return dic
        pass

    def get_region_instance(self, area):
        '''获取资源服务器函数
        :param region_area: 可用区域
        :return: 资源详情 type: json字符串
        '''
        req_url = self.generate_req_url(region_area=area)
        # responseData = urllib.request.urlopen(req_url).read().decode("utf-8")
        try:
            r = requests.get(req_url)
            if r.status_code == 200:
                context = r.text
                instance_dic = self.json_to_dict(context)
                instance_list = []
                if instance_dic["Response"]["TotalCount"] > 0:
                    for instance in instance_dic.get("Response").get("InstanceSet"):
                        instance_list.append(instance)
                    return instance_list
        except Exception as e:
            return str(e)

    @property
    def get_all_region(self, action="DescribeRegions"):
        '''获取所有地域列表参数
        :return: 服务器地域列表
        '''
        req_url = self.generate_req_url(action)
        r = requests.get(req_url)
        try:
            if r.status_code == 200:
                context = r.text
                regions_dic = self.json_to_dict(context)
                region_list = []
                for region in regions_dic["Response"]["RegionSet"]:
                    if region["RegionState"] == "AVAILABLE":
                        region_list.append(region["Region"])
                return region_list
            else:
                return None
        except Exception:
            return None


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

    def get_region_instance_detail(self, region_id, region_endpoint):
        '''get instances from one special region
        :param region_id: a string,regionID,区域id ,egg:`cn-qingdao`
        :return: a list, all instances
        '''
        client = AcsClient(self.secret_id, self.secret_key, region_id)
        request = self.__common_request_settings
        request.set_domain(region_endpoint)
        request.set_action_name("DescribeInstances")
        request.add_query_param('RegionId', region_id)
        try:
            response = client.do_action_with_exception(request)
            str_response = str(response, encoding="utf-8")
            result = json.loads(str_response).get('Instances').get('Instance')

            if result:
                self.instances.append(result)
            else:
                return
        except Exception:
            pass

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
        regions = self.get_all_regions
        if isinstance(regions,dict):
            return regions
        else:
            tasks = []
            for ins in regions:
                t = threading.Thread(target=self.get_region_instance_detail,
                                     args=(ins["RegionId"], ins["RegionEndpoint"],))
                tasks.append(t)

            for t in tasks:
                t.start()

            for t in tasks:
                if t.is_alive():
                    t.join()

            return None


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
        Tect = TencentInstancesByAk(secret_id, secret_key)
        regin_list = Tect.get_all_region
        instances = []
        if not regin_list:
            return None
        for area in regin_list:
            instance_data = Tect.get_region_instance(area=area)
            if instance_data != None:
                for ins in instance_data:
                    instances.append(ins)
            else:
                continue
        return instances
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
                    asset_dict["admin_user"] = get_object_or_none(AdminUser, name=v)

                elif k == "PublicIpAddresses":
                    if isinstance(v, list):
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
                    asset_dict["admin_user"] = get_object_or_none(AdminUser, name=v)

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
    if node and asset:
        asset.nodes.add(node)


if __name__ == "__main__":
    secretId = "AKIDZyGQXbErpY4MPDl7D4g3HH2c5KL8Y8G8"
    secretKey = "kFUTDk38yZw4xc5JHzRdZFfspWxDE0Xq"
    cloud_name = "Qcloud"
    print(Instances(secretId, secretKey, cloud_name))
