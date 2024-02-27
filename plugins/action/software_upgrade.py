#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
from time import sleep

from ansible.errors import AnsibleActionFail, AnsibleConnectionFailure
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import (
    ZPECloudAPI,
)
from ansible_collections.zpe.zpecloud.plugins.plugin_utils.utils import (
    exponential_backoff_delay,
)
from ansible_collections.zpe.zpecloud.plugins.plugin_utils.types import StringError


display = Display()

MINUTE = 60  # seconds


class ActionModule(ActionBase):
    """Action module used to apply software upgrade for Nodegrid devices over ZPE Cloud API."""

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("version", "allow_downgrade"))
    _requires_connection = False

    def _log_info(self, message: str) -> None:
        """Log information."""
        display.v(
            f"ZPE Cloud software upgrade action - Host ID: {self.host_zpecloud_id} - Host SN: {self.host_serial_number} - {message}."
        )

    def _log_warning(self, message: str) -> None:
        """Log warning."""
        display.warning(
            f"ZPE Cloud software upgrade action - Host ID: {self.host_zpecloud_id} - Host SN: {self.host_serial_number} - {message}."
        )

    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)
        self._api_session = None

        # id used to reference Nodegrid device in ZPE Cloud
        self.host_zpecloud_id = None
        self.host_serial_number = None
        self.timeout_wait_job_finish = 60 * MINUTE  # seconds
        self.max_delay_wait_job_finish = 3 * MINUTE  # seconds

    def _create_api_session(self) -> None:
        """Get credential information from user and create an authenticate session to ZPE Cloud."""
        url = self.get_option("url", None) or os.environ.get("ZPECLOUD_URL", None)

        # default for url
        if url is None:
            url = "https://zpecloud.com"

        username = self.get_option("username", None) or os.environ.get(
            "ZPECLOUD_USERNAME", None
        )
        if username is None:
            raise AnsibleConnectionFailure(
                "Could not retrieve ZPE Cloud username from plugin configuration or environment."
            )

        password = self.get_option("password", None) or os.environ.get(
            "ZPECLOUD_PASSWORD", None
        )
        if password is None:
            raise AnsibleConnectionFailure(
                "Could not retrieve ZPE Cloud password from plugin configuration or environment."
            )

        organization = self.get_option("organization", None) or os.environ.get(
            "ZPECLOUD_ORGANIZATION", None
        )

        try:
            self._api_session = ZPECloudAPI(url)
        except Exception as err:
            raise AnsibleConnectionFailure(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        result, err = self._api_session.authenticate_with_password(username, password)
        if err:
            raise AnsibleConnectionFailure(
                f"Failed to authenticate on ZPE Cloud. Error: {err}."
            )

        if organization:
            result, err = self._api_session.change_organization(organization)
            if err:
                raise AnsibleConnectionFailure(
                    f"Failed to switch organization. Error: {err}."
                )

    def _validate_version(version: str) -> None:
        if version is None:
            raise AnsibleActionFail("Version parameter is required.")

        # regex

    def run(self, tmp=None, task_vars=None):
        display.v("-----> software upgrade init")
        if task_vars is None:
            task_vars = dict()

        # Get arguments from task
        version = self._task.args.get('version', None)
        allow_downgrade = self._task.args.get('allow_downgrade', False)

        # Validate parameters
        self._validate_version(version)

        display.v(f"desired version: {version}")
        display.v(f"allow downgrade: {allow_downgrade}")

        host_serial_number = self._play_context.remote_addr

        display.v(f"serial number: {host_serial_number}")

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        # Create API session for ZPE Cloud
        self._create_api_session()

        # Check current device version, and check upgrade or downgrade
        # self.

        # Apply software upgrade profile

        # Check software upgrade job status

        # Wait device to get online again

        # Check if device was upgrade by checking its version

        #if self._task.args and "msg" in self._task.args:
        #    msg = self._task.args.get("msg")

        result["failed"] = True
        result["msg"] = msg
        return result
