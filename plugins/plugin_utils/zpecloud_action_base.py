#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

from ansible.errors import AnsibleActionFail
from ansible.plugins.action import ActionBase

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import (
    ZPECloudAPI,
)


class ZPECloudActionBase(ActionBase):
    """Base action module used for Ansible actions that interacts with ZPE Cloud API."""

    def __init__(self, *args, **kwargs):
        super(ZPECloudActionBase, self).__init__(*args, **kwargs)
        self._api_session = None

        # id used to reference Nodegrid device in ZPE Cloud
        self.host_zpecloud_id = None
        self.host_serial_number = None

    def _create_api_session(self) -> None:
        """Get credential information from user and create an authenticate session to ZPE Cloud."""
        connection_vars = self._connection._options
        if connection_vars is None:
            raise AnsibleActionFail("Connection options are not defined.")

        url = connection_vars.get("url", None) or os.environ.get("ZPECLOUD_URL", None)

        # default for url
        if url is None:
            url = "https://zpecloud.com"

        username = connection_vars.get("username", None) or os.environ.get(
            "ZPECLOUD_USERNAME", None
        )
        if username is None:
            raise AnsibleActionFail(
                "Could not retrieve ZPE Cloud username from plugin configuration or environment."
            )

        password = connection_vars.get("password", None) or os.environ.get(
            "ZPECLOUD_PASSWORD", None
        )
        if password is None:
            raise AnsibleActionFail(
                "Could not retrieve ZPE Cloud password from plugin configuration or environment."
            )

        organization = connection_vars.get("organization", None) or os.environ.get(
            "ZPECLOUD_ORGANIZATION", None
        )

        try:
            self._api_session = ZPECloudAPI(url)
        except Exception as err:
            raise AnsibleActionFail(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        result, err = self._api_session.authenticate_with_password(username, password)
        if err:
            raise AnsibleActionFail(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        if organization:
            result, err = self._api_session.change_organization(organization)
            if err:
                raise AnsibleActionFail(f"Failed to switch organization. Error: {err}.")
