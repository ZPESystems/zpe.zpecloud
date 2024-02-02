#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
from typing import List, Dict, Union, Tuple
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class MissingDependencyError(Exception):
    """ System does not have necessary dependency. """
    pass


class ZPECloudAPI:
    timeout = 30

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

    def _post(self, url: str, data: Dict, headers: Dict) -> Union[Tuple[str, str], Tuple[str, None]]:
        r = self._zpe_cloud_session.post(url=url, data=data, timeout=self.timeout, headers=headers)

        if r.status_code == 200:
            return r.text, None
        else:
            return "", r.reason

    def _get(self, url: str, headers: Dict) -> Union[Tuple[str, str], Tuple[str, None]]:
        r = self._zpe_cloud_session.get(url=url, timeout=self.timeout, headers=headers)

        if r.status_code == 200:
            return r.text, None
        else:
            return "", r.reason

    def authenticate_with_password(self, username: str, password: str) -> Union[Tuple[bool, str], Tuple[bool, None]]:
        payload = {
            "email": username,
            "password": password
        }
        content, err = self._post(url=f"{self._url}/user/auth", data=payload, headers={})
        if err:
            return False, err

        response = json.loads(content)
        self._organization_name = response.get("company", {}).get("business_name", None)

        return True, None

    def change_organization(self, organization_name: str) -> Union[Tuple[bool, str], Tuple[bool, None]]:
        if self._organization_name == organization_name:
            return True, None

        content, err = self._get(url=f"{self._url}/account/company",
                                 headers={"Content-Type": "application/json"})
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
            return False, f"Organization {organization_name} was not found or not authorized"

        content, err = self._post(url=f"{self._url}/user/auth/{self._company_id}", data={},
                                  headers={"Content-Type": "application/json"})
        if err:
            return False, err

        self._organization_name = organization_name

        return True, None

    def get_available_devices(self) -> Union[Tuple[List[Dict], None], Tuple[None, str]]:
        content, err = self._get(url=f"{self._url}/device?enrolled=0",
                                 headers={"Content-Type": "application/json"})
        if err:
            return None, err

        devices = json.loads(content)
        devices = devices.get("list")

        return devices, None

    def get_enrolled_devices(self) -> Union[Tuple[List[Dict], None], Tuple[None, str]]:
        content, err = self._get(url=f"{self._url}/device?enrolled=1",
                                 headers={"Content-Type": "application/json"})
        if err:
            return None, err

        devices = json.loads(content)
        devices = devices.get("list")

        return devices, None

    def get_groups(self) -> Union[Tuple[List[Dict], None], Tuple[None, str]]:
        content, err = self._get(url=f"{self._url}/group",
                                 headers={"Content-Type": "application/json"})
        if err:
            return None, err

        groups = json.loads(content)
        groups = groups.get("list")

        return groups, None

    def get_sites(self) -> Union[Tuple[List[Dict], None], Tuple[None, str]]:
        content, err = self._get(url=f"{self._url}/site",
                                 headers={"Content-Type": "application/json"})
        if err:
            return None, err

        sites = json.loads(content)
        sites = sites.get("list")

        return sites, None

    def get_custom_fields(self) -> Union[Tuple[List[Dict], None], Tuple[None, str]]:
        content, err = self._get(url=f"{self._url}/template-custom-field?limit=10000",
                                 headers={"Content-Type": "application/json"})
        if err:
            return None, err

        custom_fields = json.loads(content)
        custom_fields = custom_fields.get("list")

        return custom_fields, None
