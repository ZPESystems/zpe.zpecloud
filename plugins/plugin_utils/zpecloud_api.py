# license

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

# import system things

# some trys to check if requirements are in place

# TODO - create new errors for API

# import ansible things
from ansible.utils.display import Display
import requests
import json
from typing import Optional, List, Dict

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ansible.utils.display import Display

class MissingDependencyError(Exception):
    """ System does not have necessary dependecy. """
    pass

display = Display()

class ZPECloudAPI:
    def __init__(self, url: str) -> None:
        if not HAS_REQUESTS:
            raise MissingDependencyError("Please install python requests library.")

        self._url = url
        # validate if url is valid and convert to api

    def authenticate_with_password(self, username: str, password: str) -> None:
        #self._url = "https://api.test-zpecloud.com"
        # check if url contains api
        # split and append api

        self._username = username
        self._password = password
        # TODO - validate user and password, and raise error

        # authentication
        # test
        payload = {
            "email": self._username,
            "password": self._password
        }

        self._zpe_cloud_session = requests.Session()
        r = self._zpe_cloud_session.post(url=f"{self._url}/user/auth", data=payload)

        # TODO - validate response

            

    def change_company(self, organization_name: str) -> bool:
        r = self._zpe_cloud_session.post(url=f"{self._url}/user/auth/{self._company_id}")
        # TODO - create a function to change user
        # TODO - validate status code
        # change organization
        self._organization = organization_name
        if self._organization:
            r = self._zpe_cloud_session.get(url=f"{self._url}/account/company")
            # TODO - validate response
            # TODO - create a functions for each endpoint

            self._company_id = None
            companies = json.loads(r.text)
            for company in companies:
                name = company.get("business_name", None)

                if name == self._organization:
                    self._company_id = company.get("id", None)
                    break

            if self._company_id is None:
                raise ValueError("company not found")
            # TODO - raise another error

            # TODO - check why calling /user/auth is returning 403

    def get_organization_info(self) -> Dict:
        pass


    def get_on_premise_devices(self) -> List[Dict]:
        url=f"{self._url}/device/on-premise"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        devices = json.loads(r.text)
        devices = devices.get("list")
        # assert it is a list
        return devices

    def get_available_devices(self) -> List[Dict]:
        # make request
        # what means company_name == false?
        url=f"{self._url}/device?enrolled=0"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        devices = json.loads(r.text)
        devices = devices.get("list")
        # assert it is a list
        return devices

    def get_enrolled_devices(self) -> List[Dict]:
        # make request
        # what means company_name == false?
        url=f"{self._url}/device?enrolled=1"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        devices = json.loads(r.text)
        devices = devices.get("list")
        # assert it is a list
        return devices

    def get_groups(self) -> List[Dict]:
        # make request
        # what means company_name == false?
        url=f"{self._url}/group"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        groups = json.loads(r.text)
        groups = groups.get("list")
        # assert it is a list
        return groups

    def get_sites(self) -> List[Dict]:
        # make request
        # what means company_name == false?
        url=f"{self._url}/site"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        sites = json.loads(r.text)
        sites = sites.get("list")
        # assert it is a list
        return sites
    
    def get_custom_fields(self) -> List[Dict]:
        # make request
        # what means company_name == false?
        url=f"{self._url}/template-custom-field?limit=1000"
        r = self._zpe_cloud_session.get(url)
        # assert it returns 200
        custom_fields = json.loads(r.text)
        custom_fields = custom_fields.get("list")
        # assert it is a list
        return custom_fields





""""

AWS STS session token for use with temporary credentials.

See the AWS documentation for more information about access tokens https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys.

The AWS_SESSION_TOKEN, AWS_SECURITY_TOKEN or EC2_SECURITY_TOKEN environment variables may also be used in decreasing order of preference.

The security_token and profile options are mutually exclusive.

Aliases aws_session_token and session_token were added in release 3.2.0, with the parameter being renamed from security_token to session_token in release 6.0.0.

The security_token, aws_security_token, and access_token aliases have been deprecated and will be removed in a release after 2024-12-01.

Support for the EC2_SECRET_KEY and AWS_SECURITY_TOKEN environment variables has been deprecated and will be removed in a release after 2024-12-01.
"""


""""
The password of the vSphere vCenter server.

If the value is not specified in the task, the value of environment variable VMWARE_PASSWORD will be used instead.

# Sample configuration file for VMware Host dynamic inventory
    plugin: community.vmware.vmware_host_inventory
    strict: false
    hostname: 10.65.223.31
    username: administrator@vsphere.local
    password: Esxi@123$%
    validate_certs: false
    with_tags: true

"""


""""
#Using auth token instead of username/password
plugin: community.zabbix.zabbix_inventory
server_url: https://zabbix.com
auth_token: 3bc3dc85e13e2431812e7a32fa8341cbcf378e5101356c015fdf2e35fd511b06
validate_certs: false

# Simple Inventory Plugin example
# This will create an inventory with details from zabbix such as applications name, applicaitonids, Parent Template Name, and group membership name
#It will also create 2 ansible inventory groups for enabled and disabled hosts in zabbix based on the status field.
plugin: community.zabbix.zabbix_inventory
server_url: https://zabbix.com
login_user: Admin
login_password: password
host_zapi_query:
  selectApplications: ['name', 'applicationid']
  selectParentTemplates: ['name']
  selectGroups: ['name']
validate_certs: false
groups:
  enabled: zbx_status == "0"
  disabled: zbx_status == "1"


"""

"""
Notes
API Reference: https://cloud.google.com/appengine/docs/admin-api/reference/rest/v1/apps.firewall.ingressRules
Official Documentation: https://cloud.google.com/appengine/docs/standard/python/creating-firewalls#creating_firewall_rules
for authentication, you can set service_account_file using the GCP_SERVICE_ACCOUNT_FILE env variable.
for authentication, you can set service_account_contents using the GCP_SERVICE_ACCOUNT_CONTENTS env variable.
For authentication, you can set service_account_email using the GCP_SERVICE_ACCOUNT_EMAIL env variable.
For authentication, you can set access_token using the GCP_ACCESS_TOKEN env variable.
For authentication, you can set auth_kind using the GCP_AUTH_KIND env variable.
For authentication, you can set scopes using the GCP_SCOPES env variable.
Environment variables values will only be used if the playbook values are not set.
The service_account_email and service_account_file options are mutually exclusive.


"""

""""
The API Endpoint for the Hetzner Cloud.

You can also set this option by using the HCLOUD_ENDPOINT environment variable.

Default: "https://api.hetzner.cloud/v1"

Configuration:

Environment variable: HCLOUD_ENDPOINT

"""


