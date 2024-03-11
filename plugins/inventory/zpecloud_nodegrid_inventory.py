#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
name: zpecloud_nodegrid_inventory
short_description: Inventory of Nodegrid devices located on ZPE Cloud
description:
  - This plugin performs the following.
  - Fetch information about device, and store it as variables (hostname, model, serial number, status, and Nodegrid version).
  - Get Nodegrid devices located on ZPE Cloud. These devices are added to the inventory as hosts, and indexed their serial number.
  - Create default groups (available, enrolled, failover, online, offline). These groups are added to the inventory with the prefix zpecloud_device_<name>.
  - Create groups based on ZPE Cloud groups. These groups are added to the inventory with the prefix zpecloud_group_<group-name>.
  - Create groups based on ZPE Cloud sites. These groups are added to the inventory with the prefix zpecloud_site_<site-name>.
  - Fetch custom fields from ZPE Cloud, and assign to devices as variables. These variables are added to the inventory with the prefix zpecloud_cf_<name>.
  - Custom fields have scopes (global, group, site, and device).
  - If multiple custom fields share the same name, inventory variable will receive the value of the scope with higher priority.
  - Device scope has higher priority, and global scope the lower.
  - It requires a YAML configuration file with name "zpecloud.yml".
notes:
  - Ansible groups names, and variables, can only include letters, numbers, and underscores. Invalid characters will be replaced by underscore.
  - If you have a ZPE Cloud site named "My site-1", it will appear on the inventory as zpecloud_site_my_site_1. The same happens for groups, and custom fields.
author:
  - Daniel Nesvera (@zpe-dnesvera)
options:
  url:
    description:
      - URL of ZPE Cloud instance.
    default: "https://zpecloud.com"
    type: string
    env:
      - name: ZPECLOUD_URL
  username:
    description:
      - Username on ZPE Cloud.
      - Required for authentication with username and password.
    required: true
    type: string
    env:
      - name: ZPECLOUD_USERNAME
  password:
    description:
      - User password.
      - Required for authentication with username and password.
    type: string
    required: true
    env:
      - name: ZPECLOUD_PASSWORD
  organization:
    description:
      - Organization name inside ZPE Cloud. Used to switch organization if user has accounts in multiple organizations.
      - This field is case sensitive.
    type: string
    env:
      - name: ZPECLOUD_ORGANIZATION
requirements:
  - requests
"""

EXAMPLES = r"""
# Create a file named "zpecloud.yml" inside directory from inventory, and copy content from samples below.

# Sample configuration file for dynamic inventory based on ZPE Cloud. The authentication here is based on user and password.
plugin: zpe.zpecloud.zpecloud_nodegrid_inventory
url: https://zpecloud.com
username: myuser@mycompany.com
password: mysecurepassword

# Sample configuration file for dynamic inventory based on ZPE Cloud. It will authenticate and switch to second company.
plugin: zpe.zpecloud.zpecloud_nodegrid_inventory
url: https://zpecloud.com
username: myuser@mycompany.com
password: mysecurepassword
organization: "My second organization"
"""

import re
import os
from typing import Dict, List

from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.errors import AnsibleParserError

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import (
    ZPECloudAPI,
)


class ZPECloudMissingBodyInfoError(Exception):
    """Raised if expected information is not found on response body."""

    pass


class ZPECloudDefaultCustomField(Exception):
    """Raised once default custom field is created. Ansible will not use default ones."""

    pass


class ZPECloudDisabledCustomField(Exception):
    """Raised once custom field is disabled on ZPE Cloud."""

    pass


class GroupPrefix:
    """Prefixes used to differentiate inventory from ZPE Cloud from user defined one."""

    GROUP = "zpecloud_group_"
    SITE = "zpecloud_site_"
    DEVICE = "zpecloud_device_"
    CUSTOM_FIELD = "zpecloud_cf_"


class ZPECloudDefaultGroups:
    """Default groups to aggregate Nodegrid devices."""

    DEVICE_ENROLLED = f"{GroupPrefix.DEVICE}enrolled"
    DEVICE_AVAILABLE = f"{GroupPrefix.DEVICE}available"
    DEVICE_ONLINE = f"{GroupPrefix.DEVICE}online"
    DEVICE_OFFLINE = f"{GroupPrefix.DEVICE}offline"
    DEVICE_FAILOVER = f"{GroupPrefix.DEVICE}failover"


class AvailabilityStatus:
    """Availability status of Nodegrid devices."""

    ONLINE = "online"
    OFFLINE = "offline"
    FAILOVER = "failover"


class EnrollStatus:
    """ "Enrollment status of Nodegrid devices."""

    ENROLLED = "enrolled"
    AVAILABLE = "available"


class CustomFieldScope:
    """ "Scope of custom fields."""

    GLOBAL = "global"
    GROUP = "group"
    SITE = "site"
    DEVICE = "device"


def name_sanitization(name: str) -> str:
    """Sanitize names of hosts, groups, and variables, to be complaint with requirements from Ansible."""
    regex = re.compile(r"[^A-Za-z0-9\_]")
    name = name.lower()
    return regex.sub("_", name)


class ZPECloudHost:
    """Object to represent a Nodegrid device inside Ansible inventory."""

    def __init__(self, device_info: Dict, enroll_status: EnrollStatus) -> None:
        if not isinstance(device_info, Dict):
            raise TypeError("Dictionary expected.")

        device_id = device_info.get("id", None)
        if device_id is None:
            raise ZPECloudMissingBodyInfoError("Failed to get ID from Nodegrid device.")
        else:
            self.device_id = device_id

        serial_number = device_info.get("serial_number", None)
        if serial_number is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed to get serial number from Nodegrid device. Hostname: {device_info.get('hostname')}."
            )
        else:
            self.serial_number = serial_number

        self.enroll_status = enroll_status

        hostname = device_info.get("hostname", None)
        if hostname is None:
            self.hostname = ""
        else:
            self.hostname = hostname

        model = device_info.get("model", None)
        if model is None:
            self.model = ""
        else:
            self.model = model

        version = device_info.get("version", None)
        if version is None:
            self.version = ""
        else:
            version = re.search("^v[0-9.]*", version)
            if version is None:
                self.version = ""
            else:
                self.version = version.group().replace("v", "")

        status = device_info.get("device_status")
        if status is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed to get status from Nodegrid device. Hostname: {device_info.get('hostname')}"
            )
        else:
            status = status.lower()

        if status == AvailabilityStatus.ONLINE:
            self.status = AvailabilityStatus.ONLINE
        elif status == AvailabilityStatus.FAILOVER:
            self.status = AvailabilityStatus.FAILOVER
        else:
            self.status = AvailabilityStatus.OFFLINE

        site = device_info.get("site", None)
        if site:
            self.site_id = site.get("id", None)
        else:
            self.site_id = None

        groups = device_info.get("groups", None)
        self.group_ids = []
        if groups:
            for g in groups:
                group_id = g.get("id", None)
                if group_id:
                    self.group_ids.append(group_id)


class ZPECloudGroup:
    """Object to represent a ZPE Cloud group inside Ansible inventory."""

    def __init__(self, group_info: Dict) -> None:
        if not isinstance(group_info, Dict):
            raise TypeError("Dictionary expected.")

        group_id = group_info.get("id", None)
        if group_id is None:
            raise ZPECloudMissingBodyInfoError("Failed to get ID from ZPE Cloud group.")
        else:
            self.group_id = group_id

        name = group_info.get("name", None)
        if name is None:
            raise ZPECloudMissingBodyInfoError(
                "Failed to get name from ZPE Cloud group."
            )
        else:
            name = name_sanitization(name)
            self.name = f"{GroupPrefix.GROUP}{name}"


class ZPECloudSite:
    """Object to represent a ZPE Cloud site inside Ansible inventory."""

    def __init__(self, site_info: Dict) -> None:
        if not isinstance(site_info, Dict):
            raise TypeError("Dictionary expected.")

        site_id = site_info.get("id", None)
        if site_id is None:
            raise ZPECloudMissingBodyInfoError("Failed to get ID from ZPE Cloud site.")
        else:
            self.site_id = site_id

        name = site_info.get("name", None)
        if name is None:
            raise ZPECloudMissingBodyInfoError(
                "Failed to get name from ZPE Cloud site."
            )
        else:
            name = name_sanitization(name)
            self.name = f"{GroupPrefix.SITE}{name}"


class ZPECustomFields:
    """Object to represent a ZPE Cloud custom field inside Ansible inventory."""

    def __init__(self, custom_field_info: Dict) -> None:
        if not isinstance(custom_field_info, Dict):
            raise TypeError("Dictionary expected.")

        name = custom_field_info.get("name", None)
        if name is None:
            raise ZPECloudMissingBodyInfoError(
                "Failed to get name from ZPE Cloud custom field."
            )
        elif "." in name:
            raise ZPECloudDefaultCustomField(
                f"Default custom fields from ZPE Cloud is not used on Ansible. Custom field name: {name}."
            )
        else:
            name = name_sanitization(name)
            self.name = f"{GroupPrefix.CUSTOM_FIELD}{name}"

        enabled = custom_field_info.get("enabled", False)
        if not enabled:
            raise ZPECloudDisabledCustomField(f"Custom field {name} is disabled.")

        reference = custom_field_info.get("reference", None)

        scope = custom_field_info.get("scope", None)
        if scope is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed to get scope from ZPE CLoud custom field. Custom field name: {name}."
            )
        else:
            self.scope = scope

        if scope == CustomFieldScope.GLOBAL:
            self.reference = reference

        elif (
            scope == CustomFieldScope.GROUP
            or scope == CustomFieldScope.SITE
            or scope == CustomFieldScope.DEVICE
        ):
            # reference will be null for global, but must have value for other scopes
            if reference is None:
                raise ZPECloudMissingBodyInfoError(
                    f"Failed to get reference from ZPE Cloud custom field. Custom field name: {name}."
                )

            if scope == CustomFieldScope.DEVICE:
                serial_number = reference.split(" ")[-1]
                if len(serial_number) == 0:
                    raise ZPECloudMissingBodyInfoError(
                        f"Failed to get reference from ZPE Cloud custom field with device scope. Custom field name: {name}."
                    )

                self.reference = serial_number

            else:
                self.reference = name_sanitization(reference)

        else:
            raise ZPECloudMissingBodyInfoError(
                f"Invalid scope from ZPE Cloud custom field. Custom field name: {name}."
            )

        value = custom_field_info.get("value", None)
        if value is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed to get value from ZPE Cloud custom field. Custom field name: {name}."
            )
        else:
            self.value = value

        enabled = custom_field_info.get("enabled", None)
        if enabled is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed get enabled property from ZPE Cloud custom field. Custom field name: {name}."
            )
        else:
            self.enabled = enabled

        dynamic = custom_field_info.get("dynamic", None)
        if dynamic is None:
            raise ZPECloudMissingBodyInfoError(
                f"Failed to get dynamic property from ZPE Cloud custom field. Custom field name: {name}."
            )
        else:
            self.dynamic = dynamic


class InventoryModule(BaseInventoryPlugin):
    NAME = "zpe.zpecloud.zpecloud_nodegrid_inventory"

    def _validate_devices(
        self, devices: List, enroll_status: EnrollStatus
    ) -> List[ZPECloudHost]:
        valid_devices = []
        for d in devices:
            try:
                valid_devices.append(ZPECloudHost(d, enroll_status))
            except Exception as err:
                self.display.warning(
                    f"Failed to validate Nodegrid device. Error: {err}"
                )

        return valid_devices

    def _validate_sites(self, sites: List) -> List[ZPECloudSite]:
        valid_sites = []
        for s in sites:
            try:
                valid_sites.append(ZPECloudSite(s))
            except Exception as err:
                self.display.warning(f"Failed to validate ZPE Cloud site. Error: {err}")

        return valid_sites

    def _validate_groups(self, groups: List) -> List[ZPECloudGroup]:
        valid_groups = []
        for g in groups:
            try:
                valid_groups.append(ZPECloudGroup(g))
            except Exception as err:
                self.display.warning(
                    f"Failed to validate ZPE Cloud group. Error: {err}"
                )

        return valid_groups

    def _validate_custom_fields(self, custom_fields: List) -> List[ZPECustomFields]:
        valid_custom_fields = []
        for cf in custom_fields:
            try:
                valid_custom_fields.append(ZPECustomFields(cf))
            except ZPECloudDefaultCustomField as msg:
                self.display.debug(f"Custom field will be discarded. {msg}")
            except ZPECloudDisabledCustomField as msg:
                self.display.debug(f"Custom field will be discarded. {msg}")
            except Exception as err:
                self.display.warning(f"Failed to validate custom field. Error: {err}")

        return valid_custom_fields

    def _parse_devices(
        self, zpecloud_groups: List[ZPECloudGroup], zpecloud_sites: List[ZPECloudSite]
    ) -> List[ZPECloudHost]:
        device_list = []
        enrolled_devices, err = self._api_session.get_enrolled_devices()
        if err:
            raise AnsibleParserError(
                f"Failed to get devices from enroll tab. Error: {err}."
            )

        device_list += self._validate_devices(enrolled_devices, EnrollStatus.ENROLLED)

        available_devices, err = self._api_session.get_available_devices()
        if err:
            raise AnsibleParserError(
                f"Failed to get devices from available tab. Error: {err}."
            )

        device_list += self._validate_devices(available_devices, EnrollStatus.AVAILABLE)

        if len(device_list) == 0:
            AnsibleParserError("No device found in ZPE Cloud.")

        discarded_count = (
            len(available_devices) + len(enrolled_devices) - len(device_list)
        )
        if discarded_count > 0:
            self.display.warning(
                f"{discarded_count} Nodegrid devices were discarded due required fields missing. "
            )

        # Devices are mapped to sites, and groups, by its IDs but name is required to store inside inventory
        # Create a lookup table for sites, and groups, mapping id to names
        group_lookup = {}
        for g in zpecloud_groups:
            group_lookup[g.group_id] = g.name

        site_lookup = {}
        for s in zpecloud_sites:
            site_lookup[s.site_id] = s.name

        for device in device_list:
            # add host
            host_id = device.serial_number
            self.inventory.add_host(host_id)

            # set host variables
            self.inventory.set_variable(host_id, "serial_number", device.serial_number)
            self.inventory.set_variable(host_id, "zpecloud_id", device.device_id)
            self.inventory.set_variable(host_id, "hostname", device.hostname)
            self.inventory.set_variable(host_id, "version", device.version)
            self.inventory.set_variable(host_id, "status", device.status)
            self.inventory.set_variable(host_id, "model", device.model)

            # assign device to group based on enrollment status
            if device.enroll_status == EnrollStatus.ENROLLED:
                self.inventory.add_child(ZPECloudDefaultGroups.DEVICE_ENROLLED, host_id)
            else:
                self.inventory.add_child(
                    ZPECloudDefaultGroups.DEVICE_AVAILABLE, host_id
                )

            # assign device to group based on availability status
            if device.status == AvailabilityStatus.ONLINE:
                self.inventory.add_child(ZPECloudDefaultGroups.DEVICE_ONLINE, host_id)
            elif device.status == AvailabilityStatus.FAILOVER:
                self.inventory.add_child(ZPECloudDefaultGroups.DEVICE_FAILOVER, host_id)
            else:
                self.inventory.add_child(ZPECloudDefaultGroups.DEVICE_OFFLINE, host_id)

            # assign device to ZPE Cloud sites
            if device.site_id:
                site_n = site_lookup.get(device.site_id, None)
                if site_n:
                    self.inventory.add_child(site_n, host_id)

            # assign device to ZPE Cloud groups
            for group_id in device.group_ids:
                group_n = group_lookup.get(group_id, None)
                if group_n:
                    self.inventory.add_child(group_n, host_id)

        return device_list

    def _parse_groups(self) -> List[ZPECloudGroup]:
        groups, err = self._api_session.get_groups()
        if err:
            self.display.v(f"Failed to get groups from ZPE Cloud. Error: {err}.")
            return []

        group_list = self._validate_groups(groups)
        for group in group_list:
            self.inventory.add_group(group.name)

        return group_list

    def _parse_sites(self) -> List[ZPECloudSite]:
        sites, err = self._api_session.get_sites()
        if err:
            self.display.v(f"Failed to get sites from ZPE Cloud. Error: {err}.")
            return []

        site_list = self._validate_sites(sites)
        for site in site_list:
            self.inventory.add_group(site.name)

        return site_list

    def _parse_custom_fields(self, devices: List[ZPECloudHost]) -> None:
        custom_fields, err = self._api_session.get_custom_fields()
        if err:
            self.display.v(f"Failed to get custom fields from ZPE Cloud. Error: {err}.")
            return []

        cf_list = self._validate_custom_fields(custom_fields)

        # custom fields reference devices by its hostname, then is necessary to create a lookup table from
        # hostname to serial number that is used as index of the inventory
        device_lookup = {}
        for d in devices:
            device_lookup[d.serial_number] = d

        # get a dictionary of all groups already inside inventory
        inventory_groups = self.inventory.get_groups_dict()

        for cf in cf_list:
            if cf.scope == CustomFieldScope.GLOBAL:
                self.inventory.set_variable("all", cf.name, cf.value)

            elif cf.scope == CustomFieldScope.GROUP:
                # check if already exists a group inside inventory
                group_name = f"{GroupPrefix.GROUP}{cf.reference}"
                if inventory_groups.get(group_name, None):
                    self.inventory.set_variable(group_name, cf.name, cf.value)

            elif cf.scope == CustomFieldScope.SITE:
                # check if already exists a group inside inventory
                site_name = f"{GroupPrefix.SITE}{cf.reference}"
                if inventory_groups.get(site_name, None):
                    self.inventory.set_variable(site_name, cf.name, cf.value)

            else:
                if device_lookup.get(cf.reference, None):
                    self.inventory.set_variable(cf.reference, cf.name, cf.value)

    def verify_file(self, path):
        """return true/false if this is possibly a valid file for this plugin to consume"""
        valid = False
        if super(InventoryModule, self).verify_file(path):
            # base class verifies that file exists and is readable by current user
            if path.endswith(("zpecloud.yaml", "zpecloud.yml")):
                valid = True
        return valid

    def _create_api_session(self) -> None:
        url = self.get_option("url", None) or os.environ.get("ZPECLOUD_URL", None)

        # default for url
        if url is None:
            url = "https://zpecloud.com"

        username = self.get_option("username", None) or os.environ.get(
            "ZPECLOUD_USERNAME", None
        )
        if username is None:
            raise AnsibleParserError(
                "Could not retrieve ZPE Cloud username from plugin configuration or environment."
            )

        password = self.get_option("password", None) or os.environ.get(
            "ZPECLOUD_PASSWORD", None
        )
        if password is None:
            raise AnsibleParserError(
                "Could not retrieve ZPE Cloud password from plugin configuration or environment."
            )

        organization = self.get_option("organization", None) or os.environ.get(
            "ZPECLOUD_ORGANIZATION", None
        )

        try:
            self._api_session = ZPECloudAPI(url)
        except Exception as err:
            raise AnsibleParserError(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        result, err = self._api_session.authenticate_with_password(username, password)
        if err:
            raise AnsibleParserError(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        if organization:
            result, err = self._api_session.change_organization(organization)
            if err:
                raise AnsibleParserError(
                    f"Failed to switch organization. Error: {err}."
                )

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path)
        self._read_config_data(path)

        # get credentials from file and create an API session to ZPE Cloud
        self.display.v("Authenticating on ZPE Cloud ...")
        self._create_api_session()

        # create default groups
        self.inventory.add_group(ZPECloudDefaultGroups.DEVICE_ENROLLED)
        self.inventory.add_group(ZPECloudDefaultGroups.DEVICE_AVAILABLE)
        self.inventory.add_group(ZPECloudDefaultGroups.DEVICE_ONLINE)
        self.inventory.add_group(ZPECloudDefaultGroups.DEVICE_OFFLINE)
        self.inventory.add_group(ZPECloudDefaultGroups.DEVICE_FAILOVER)

        # create groups based on ZPE Cloud groups
        self.display.v("Fetching groups from ZPE Cloud and creating Ansible groups ...")
        zpecloud_groups = self._parse_groups()

        # create groups based on ZPE Cloud sites
        self.display.v("Fetching sites from ZPE Cloud and creating Ansible groups ...")
        zpecloud_sites = self._parse_sites()

        # fetch devices from ZPE Cloud and populate hosts
        self.display.v(
            "Fetching Nodegrid devices from ZPE Cloud and creating Ansible hosts ..."
        )
        zpecloud_devices = self._parse_devices(zpecloud_groups, zpecloud_sites)

        # fetch custom fields from ZPE Cloud
        self.display.v(
            "Fetching custom fields devices from ZPE Cloud and creating Ansible variables ..."
        )
        self._parse_custom_fields(zpecloud_devices)
