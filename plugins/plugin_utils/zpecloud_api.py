#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
from typing import List, Dict, Union, Tuple, Any
from urllib.parse import urlparse
from datetime import datetime

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.types import (
    StringError,
    BooleanError,
    DictError,
    ListDictError,
)

class MissingDependencyError(Exception):
    """System does not have necessary dependency."""

    pass


class ZPECloudAPI:
    timeout = 100
    query_limit = 50

    def __init__(self, url: str) -> None:
        if not HAS_REQUESTS:
            raise MissingDependencyError("Please install python requests library.")

        # urlparse struggles to define netloc and path without scheme
        if "http://" not in url and "https://" not in url:
            url = f"https://{url}"

        url_parts = urlparse(url)
        netloc = url_parts.netloc.replace("www.", "")

        self._url = f"https://api.{netloc}"
        self._zpe_cloud_session = requests.Session()

    def _post(self, url: str, data: Dict) -> StringError:
        r = self._zpe_cloud_session.post(url=url, data=data, timeout=self.timeout)

        if r.status_code == 200:
            return r.text, None
        else:
            return "", r.reason

    def _get(self, url: str) -> StringError:
        r = self._zpe_cloud_session.get(url=url, timeout=self.timeout)

        if r.status_code == 200:
            return r.text, None
        else:
            return "", r.reason

    def _delete(self, url: str) -> StringError:
        r = self._zpe_cloud_session.delete(url=url, timeout=self.timeout)

        if r.status_code == 204:
            return r.text, None
        else:
            return "", r.reason

    def _upload_file(self, url: str, files: Tuple) -> StringError:
        r = self._zpe_cloud_session.post(url=url, files=files, timeout=self.timeout)

        if r.status_code == 201:
            return r.text, None
        else:
            return "", r.reason

    def authenticate_with_password(
        self, username: str, password: str
    ) -> BooleanError:
        payload = {"email": username, "password": password}
        content, err = self._post(url=f"{self._url}/user/auth", data=payload)
        if err:
            return False, err

        response = json.loads(content)
        self._organization_name = response.get("company", {}).get("business_name", None)

        return True, None

    def change_organization(self, organization_name: str) -> BooleanError:
        if self._organization_name == organization_name:
            return True, None

        content, err = self._get(url=f"{self._url}/account/company")
        if err:
            return False, err

        self._company_id = None
        companies = json.loads(content)
        for company in companies:
            name = company.get("business_name", None)

            if name == organization_name:
                self._company_id = company.get("id", None)
                break

        if self._company_id is None:
            return (
                False,
                f"Organization {organization_name} was not found or not authorized",
            )

        content, err = self._post(
            url=f"{self._url}/user/auth/{self._company_id}", data={}
        )
        if err:
            return False, err

        self._organization_name = organization_name

        return True, None

    def logout(self) -> BooleanError:
        err = self._post(url=f"{self._url}/user/logout", data={})[1]
        if err:
            return False, err

        return True, None

    def _get_devices(self, enrolled: bool = True) -> ListDictError:
        if enrolled:
            enroll_param = "&enrolled=1"
        else:
            enroll_param = "&enrolled=0"

        devices = []
        while True:
            offset_url = f"{self._url}/device?{enroll_param}&offset={len(devices)}&limit={self.query_limit}"
            content, err = self._get(url=offset_url)
            if err:
                return None, err

            content = json.loads(content)
            device_count = content.get("count", None)
            if device_count is None:
                return None, "Failed to retrieve device count."

            device_list = content.get("list", None)
            if device_list is None:
                return None, "Failed to retrieve device list."

            devices += device_list
            if len(devices) >= device_count:
                break

        return devices, None

    def get_available_devices(self) -> ListDictError:
        return self._get_devices(enrolled=False)

    def get_enrolled_devices(self) -> ListDictError:
        return self._get_devices(enrolled=True)

    def get_groups(self) -> ListDictError:
        groups = []
        while True:
            offset_url = (
                f"{self._url}/group?offset={len(groups)}&limit={self.query_limit}"
            )
            content, err = self._get(url=offset_url)
            if err:
                return None, err

            content = json.loads(content)
            group_count = content.get("count", None)
            if group_count is None:
                return None, "Failed to retrieve group count."

            group_list = content.get("list", None)
            if group_list is None:
                return None, "Failed to retrieve group list."

            groups += group_list
            if len(groups) >= group_count:
                break

        return groups, None

    def get_sites(self) -> ListDictError:
        sites = []
        while True:
            offset_url = (
                f"{self._url}/site?offset={len(sites)}&limit={self.query_limit}"
            )
            content, err = self._get(url=offset_url)
            if err:
                return None, err

            content = json.loads(content)
            site_count = content.get("count", None)
            if site_count is None:
                return None, "Failed to retrieve site count."

            site_list = content.get("list", None)
            if site_list is None:
                return None, "Failed to retrieve group list."

            sites += site_list
            if len(sites) >= site_count:
                break

        return sites, None

    def get_custom_fields(self) -> ListDictError:
        custom_fields = []
        while True:
            offset_url = f"{self._url}/template-custom-field?offset={len(custom_fields)}&limit={self.query_limit}"
            content, err = self._get(url=offset_url)
            if err:
                return None, err

            content = json.loads(content)
            cf_count = content.get("count", None)
            if cf_count is None:
                return None, "Failed to retrieve custom field count."

            cf_list = content.get("list", None)
            if cf_list is None:
                return None, "Failed to retrieve custom field list."

            custom_fields += cf_list
            if len(custom_fields) >= cf_count:
                break

        return custom_fields, None

    def create_profile(self, files: Tuple) -> DictError:
        content, err = self._upload_file(url=f"{self._url}/profile", files=files)

        if err:
            return None, err

        content = json.loads(content)

        return content, None

    def delete_profile(self, profile_id: str) -> StringError:
        err = self._delete(url=f"{self._url}/profile/{profile_id}")[1]
        if err:
            return None, err

        return "", None

    def apply_profile(
        self, device_id: str, profile_id: str, schedule: datetime
    ) -> StringError:
        payload = {
            "schedule": schedule.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "is_first_connection": "false",
        }

        content, err = self._post(
            url=f"{self._url}/profile/{profile_id}/device/{device_id}", data=payload
        )

        if err:
            return None, err

        return content, None

    def get_job(self, job_id: str) -> StringError:
        content, err = self._get(url=f"{self._url}/job/{job_id}/details?jobId={job_id}")

        if err:
            return None, err

        return content, None
