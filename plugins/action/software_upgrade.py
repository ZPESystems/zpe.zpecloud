#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from datetime import datetime
import json
import re
import requests
import time
from typing import List, Dict, Optional

from ansible.errors import AnsibleActionFail
from ansible.utils.display import Display

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.utils import (
    exponential_backoff_delay,
)
from ansible_collections.zpe.zpecloud.plugins.plugin_utils.types import (
    StringError,
    BooleanError,
)

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_action_base import (
    ZPECloudActionBase,
)

display = Display()

MINUTE = 60  # seconds


class ActionModule(ZPECloudActionBase):
    """Action module used to apply software upgrade for Nodegrid devices over ZPE Cloud API."""

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("version", "allow_downgrade"))
    _requires_connection = False

    VERSION_REGEX = r"[0-9]+\.[0-9]+\.[0-9]+"

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

        self.timeout_wait_job_finish = 60 * MINUTE  # in seconds
        self.max_delay_wait_job_finish = 3 * MINUTE  # in seconds
        self.timeout_wait_device_online = 60 * MINUTE  # in seconds
        self.max_delay_wait_device_online = 3 * MINUTE  # in seconds

    def _validate_version(self, version: str) -> bool:
        """Validate if version string matches expected format."""
        if version is None:
            return False

        pattern = re.compile(self.VERSION_REGEX)
        if pattern.fullmatch(version):
            return True
        else:
            return False

    def _extract_version(self, version: str) -> Optional[str]:
        """Extract expected version format from string.
        ZPE Cloud stores version as v5.10.10 (Jan 15 2024 - 07:45:20).
        Software upgrade action expects 5.10.10."""
        pattern = re.compile(self.VERSION_REGEX)
        search_res = pattern.search(version)

        if search_res:
            return search_res.group()
        else:
            return None

    def _is_upgrade(self, cur_version: str, next_version: str) -> BooleanError:
        """Check if operation is a software upgrade, or downgrade, based on current and desired versions.
        cur_version, and next version, must follow the expected version format."""
        cur_version_parts = cur_version.split(".")
        if len(cur_version_parts) != 3:
            return (
                None,
                "Current NG OS version does not respect expected format. Version: {cur_version}.",
            )

        next_version_parts = next_version.split(".")
        if len(next_version_parts) != 3:
            return (
                None,
                "Desired NG OS version does not respect expected format. Version: {next_version}.",
            )

        for i in range(3):
            if int(next_version_parts[i]) < int(cur_version_parts[i]):
                return False, None

        return True, None

    def _get_version_id_from_list(self, version: str, content: List[Dict]) -> str:
        """Get ID from Nodegrid version based on desired version."""
        for os_entry in content:
            os_entry_name = os_entry.get("name", None)
            os_version_id = os_entry.get("id", None)

            if os_entry_name is None or os_version_id is None:
                continue

            os_version = self._extract_version(os_entry_name)
            if os_version == version:
                return os_version_id

        return None

    def _apply_software_upgrade(self, device_id: str, profile_id: str) -> str:
        """Apply software upgrade profile to device."""
        self._log_info(
            f"Applying software upgrade profile {profile_id} to device: {device_id}"
        )

        schedule = datetime.utcnow()
        err = self._api_session.apply_software_upgrade(device_id, profile_id, schedule)[
            1
        ]
        if err:
            raise AnsibleActionFail(
                f"Failed to apply software upgrade profile {profile_id} to device {self.host_serial_number}. Error: {err}."
            )

        job_id, err = self._get_software_upgrade_job_id(
            self.host_serial_number, schedule
        )
        if err:
            raise AnsibleActionFail(
                f"Failed to fetch job for software upgrade. Error: {err}."
            )

        return job_id

    def _get_software_upgrade_job_id(
        self, serial_number: str, schedule: datetime
    ) -> StringError:
        """Search last upgrade job to find job id.
        Apply software upgrade does not return the job id, then is necessary to search.
        """
        schedule_formatted = schedule.isoformat()

        # TODO - open an enhancement for this
        content, err = self._api_session.search_jobs(serial_number)
        if err:
            raise AnsibleActionFail(f"Failed to search jobs. Error: {err}.")

        resp = json.loads(content)
        job_list = resp.get("list", None)

        if job_list is None:
            raise AnsibleActionFail("Failed to get list for job search.")

        for job in job_list:
            display.v("---> job:")
            display.v(str(job))
            job_schedule = job.get("schedule", None)
            job_id = job.get("id", None)
            if job_schedule is None or job_id is None:
                self._log_info("Failed to get job or schedule from job list.")
                continue

            job_schedule_formatted = datetime.strptime(
                job_schedule, self._api_session.SCHEDULE_FORMAT
            ).isoformat()

            if schedule_formatted == job_schedule_formatted:
                return job_id, None

        return None, "Job ID not found."

    def _wait_job_to_finish(self, job_id: str) -> StringError:
        """Loop to verify status of job in ZPE Cloud."""
        request_attempt = 0
        start_time = time.time()
        while (time.time() - start_time) <= self.timeout_wait_job_finish:
            self._log_info(
                f"Checking job status for {job_id} - Attempt {request_attempt}"
            )
            content, err = self._api_session.get_job(job_id)
            if err:
                raise AnsibleActionFail(
                    f"Failed to get status for job {job_id}. Err: {err}."
                )
            content = json.loads(content)
            operation_status = content.get("operation", {}).get("status", None)
            if operation_status is None:
                raise AnsibleActionFail(f"Failed to get status for job {job_id}.")

            operation_output_file_url = content.get("output_file", None)

            if (
                operation_status == "Successful"
                and operation_output_file_url
                and len(operation_output_file_url) > 0
            ):
                self._log_info(f"Job {job_id} finished successfully")
                r = requests.get(operation_output_file_url)

                if isinstance(r.content, bytes):
                    return r.content.decode("utf-8"), None
                else:
                    return r.content, None

            elif (
                operation_status == "Failed"
                or operation_status == "Cancelled"
                or operation_status == "Timeout"
            ):
                self._log_info(f"Job {job_id} failed")

                if operation_output_file_url and len(operation_output_file_url) > 0:
                    r = requests.get(operation_output_file_url)
                    if isinstance(r.content, bytes):
                        msg = r.content.decode("utf-8")
                    else:
                        msg = r.content

                    return (
                        None,
                        f"Job finish with status {operation_status}. Output: {msg}.",
                    )

                else:
                    return (
                        None,
                        f"Job finish with status {operation_status}. Not output content.",
                    )

            delay = exponential_backoff_delay(
                request_attempt, self.max_delay_wait_job_finish
            )
            request_attempt += 1
            time.sleep(delay)

        return None, "Timeout"

    def run(self, tmp=None, task_vars=None):
        self._log_info("[run override]")
        if task_vars is None:
            task_vars = dict()

        # Get arguments from task
        version = self._task.args.get("version", None)
        allow_downgrade = self._task.args.get("allow_downgrade", False)

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        # Validate parameters
        if not self._validate_version(version):
            raise AnsibleActionFail(
                "NG OS version was not provided, or does not match the expected format."
            )

        display.v(f"desired version: {version}")
        display.v(f"allow downgrade: {allow_downgrade}")

        if self._play_context.remote_addr is None:
            raise AnsibleActionFail("Remote serial number from host was not found.")

        self.host_serial_number = self._play_context.remote_addr

        # Create API session for ZPE Cloud
        self._log_info("Authenticating on ZPE Cloud ...")
        self._create_api_session()

        # Get device id
        device, err = self._api_session.fetch_device_by_serial_number(
            self.host_serial_number
        )
        if err:
            raise AnsibleActionFail(
                f"Failed to fetch device in ZPE Cloud. Error: {err}."
            )

        self.host_zpecloud_id = device.get("id", None)
        if self.host_zpecloud_id is None:
            raise AnsibleActionFail("Failed to get device ID.")

        # Get current NG OS version on device
        current_version = device.get("version", None)
        if current_version is None:
            raise AnsibleActionFail("Failed to get current device version.")

        current_version = self._extract_version(current_version)

        display.v(f"current version: {current_version}")

        # Not necessary to proceed if device already has the desired version
        if version == current_version:
            result["changed"] = False
            result["msg"] = f"Device already on Nodegrid version {version}."
            return result

        # Check if is an upgrade or downgrade
        is_upgrade, err = self._is_upgrade(current_version, version)
        if err:
            raise AnsibleActionFail(
                "Failed to compare current NG OS version to desired version."
            )

        if not is_upgrade and not allow_downgrade:
            result["skipped"] = True
            result["msg"] = (
                f"Software downgrade is not allowed. Current version: {current_version}. Desired version: {version}."
                f" Enable allow_downgrade parameter if operation is desired."
            )
            return result

        # Get NG OS ID based on desired version
        os_versions, err = self._api_session.get_available_os_version()
        if err:
            raise AnsibleActionFail(
                "Failed to get Nodegrid OS versions from ZPE Cloud."
            )

        os_version_id = self._get_version_id_from_list(version, os_versions)
        if os_version_id is None:
            raise AnsibleActionFail("Failed to get Nodegrid OS version ID.")

        display.v(f"desired version id: {os_version_id}")

        # Apply software upgrade profile
        job_id = self._apply_software_upgrade(self.host_zpecloud_id, os_version_id)

        display.v(f"job id found: {job_id}")

        # Check software upgrade job status
        job_output, err = self._wait_job_to_finish(job_id)
        if err:
            raise AnsibleActionFail(f"Failed to apply software upgrade. Error: {err}.")

        # Check if device was upgrade by checking its version
        content, err = self._api_session.get_device_detail(self.host_zpecloud_id)
        if err:
            raise AnsibleActionFail(f"Failed to get device detail. Error: {err}.")

        content = json.loads(content)
        version_after_op = content.get("version", None)
        if current_version is None:
            raise AnsibleActionFail("Failed to get current device version.")

        version_after_op = self._extract_version(version_after_op)

        if version_after_op == version:
            result["failed"] = False
            result["changed"] = True
            result["msg"] = f"Device was upgraded to Nodegrid version {version}."
            return result

        else:
            result["failed"] = True
            result["changed"] = False
            result["msg"] = f"Failed to upgrade device to Nodegrid version {version}."
            return result
