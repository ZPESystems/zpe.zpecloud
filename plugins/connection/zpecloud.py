#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
name: zpecloud
short_description: This connection plugin allows Ansible to execute tasks on Nodegrid devices via ZPE Cloud API.
description:
  - Run commands or put/fetch files to Nodegrid device enrolled on ZPE Cloud.
  - Uses python requests library to interact with ZPE Cloud API.
author:
  - Daniel Nesvera (@zpe-dnesvera)
notes:
  - Plugin will poll ZPE Cloud API to fetch status of each job until status is successful.
  - The poll algorithm uses exponential backoff delay, and will timeout after 1 hour.
  - Plugin will check file size for put, and fetch tasks. The limit is 100Mb.
requirements:
  - requests
options:
  url:
    description:
      - URL of ZPE Cloud instance.
    default: "https://zpecloud.com"
    type: string
    vars:
      - name: ansible_zpecloud_url
    env:
      - name: ZPECLOUD_URL
  username:
    description:
      - Username on ZPE Cloud.
      - Required for authentication with username and password.
    required: true
    type: string
    vars:
      - name: ansible_zpecloud_username
    env:
      - name: ZPECLOUD_USERNAME
  password:
    description:
      - User password.
      - Required for authentication with username and password.
    type: string
    required: true
    vars:
      - name: ansible_zpecloud_password
    env:
      - name: ZPECLOUD_PASSWORD
  organization:
    description:
      - Organization name inside ZPE Cloud. Used to switch organization if user has accounts in multiple organizations.
      - This field is case sensitive.
    type: string
    vars:
      - name: ansible_zpecloud_organization
    env:
      - name: ZPECLOUD_ORGANIZATION
"""

EXAMPLES = r"""
# example playbook_nodegrid.yml
---
- name: Get uptime from Nodegrid device
  vars:
    ansible_connection: zpe.zpecloud.zpecloud
    ansible_zpecloud_username: myuser@mycompany.com
    ansible_zpecloud_password: mysecurepassword
    ansible_zpecloud_url: "https://zpecloud.com"
    ansible_zpecloud_organization: "My second organization"
  hosts: zpecloud_device_online
  gather_facts: no
  tasks:
  - name: Shell command
    shell: uptime -p
"""

import json
import os
import time
import uuid

try:
    import requests
except ImportError as err:
    REQUESTS_IMPORT_ERROR = err
else:
    REQUESTS_IMPORT_ERROR = None

from datetime import datetime
from typing import Tuple
from io import StringIO

from ansible.errors import (
    AnsibleConnectionFailure,
    AnsibleError,
    AnsibleFileNotFound,
)
from ansible.module_utils._text import to_bytes, to_text
from ansible.plugins.connection import ConnectionBase
from ansible.utils.display import Display

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import (
    ZPECloudAPI,
)
from ansible_collections.zpe.zpecloud.plugins.plugin_utils.jinja_templates import (
    render_exec_command,
    render_put_file,
    render_fetch_file,
)

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.utils import (
    read_file,
    write_file,
    encode_base64,
    decode_base64,
    compress_file,
    extract_file,
    exponential_backoff_delay,
)

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.types import StringError

display = Display()

MINUTE = 60  # seconds
MEGABYTE = 1000000  # bytes


class Connection(ConnectionBase):
    """Plugin to create a transport method between Ansible and Nodegrid device over ZPE CLOUD API."""

    transport = "zpe.zpecloud.zpecloud"
    has_pipelining = True
    filename_inside_zip = (
        "original-file"  # name of important file located inside compressed file
    )

    def _log_info(self, message: str) -> None:
        """Log information."""
        display.v(
            f"ZPE Cloud connection - Host ID: {self.host_zpecloud_id} - Host SN: {self.host_serial_number} - {message}."
        )

    def _log_warning(self, message: str) -> None:
        """Log warning."""
        display.warning(
            f"ZPE Cloud connection - Host ID: {self.host_zpecloud_id} - Host SN: {self.host_serial_number} - {message}."
        )

    def __init__(self, *args, **kwargs) -> None:
        """Initialize ZPE Cloud connection plugin."""
        super(Connection, self).__init__(*args, **kwargs)
        self._api_session = None
        # id used to reference Nodegrid device in ZPE Cloud
        self.host_zpecloud_id = None
        self.host_serial_number = None

        self.timeout_wait_job_finish = 60 * MINUTE  # seconds
        self.max_delay_wait_job_finish = 3 * MINUTE  # seconds

        self.max_file_size_put_file = 100 * MEGABYTE  # bytes
        self.max_file_size_fetch_file = 100 * MEGABYTE  # bytes

        if REQUESTS_IMPORT_ERROR:
            raise AnsibleConnectionFailure(
                "Requests library must be installed to use this plugin."
            )

        self._log_info("[__init__ override]")

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

    def _wrapper_exec_command(self, cmd: str) -> str:
        """Wrap Ansible command inside a bash command that will be executed by ZPE Cloud."""
        profile_content, err = render_exec_command(cmd)
        if err:
            raise AnsibleError(f"Failed to execute command. Error: {err}.")

        return profile_content

    def _create_profile(self, profile_content: str) -> str:
        """Create script profile."""
        profile_name = f"ansible_{uuid.uuid4()}"
        self._log_info(f"Creating profile: {profile_name}")

        description = "Script profile generated by Ansible."

        f = None
        try:
            f = StringIO(profile_content)
            payload_file = (
                ("name", (None, profile_name)),
                ("description", (None, description)),
                ("type", (None, "SCRIPT")),
                ("default", (None, "false")),
                ("is_apply_on_connect", (None, "false")),
                ("password_protected", (None, "false")),
                ("custom_command_name", (None, "")),
                ("is_custom_command_enabled", (None, "false")),
                ("language", (None, "SHELL")),
                ("dynamic", (None, "false")),
                ("file", (profile_name, f)),
            )

            response, err = self._api_session.create_profile(payload_file)

        except Exception as error:
            err = error

        finally:
            if f:
                f.close()

        if err:
            raise AnsibleError(
                f"Failed to create script profile in ZPE Cloud. Error: {err}."
            )

        profile_id = response.get("id", None)
        if profile_id is None:
            raise AnsibleError("Failed to retrieve ID from script profile.")

        return response.get("id")

    def _delete_profile(self, profile_id: str) -> None:
        """Delete script profile from ZPE Cloud."""
        err = self._api_session.delete_profile(profile_id)[1]
        if err:
            self._log_warning(
                f"Failed to delete profile from ZPE Cloud. ID: {profile_id}. Error: {err}"
            )

    def _apply_profile(self, device_id: str, profile_id: str) -> str:
        """Apply script profile to device."""
        self._log_info(f"Applying profile {profile_id} to device: {device_id}")

        schedule = datetime.utcnow()
        content, err = self._api_session.apply_profile(device_id, profile_id, schedule)
        if err:
            raise AnsibleError(
                f"Failed to apply script profile {profile_id} to device {self.host_serial_number}. Error: {err}."
            )

        resp = json.loads(content)
        job_id = resp.get("job_id")

        return job_id

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
                raise AnsibleError(
                    f"Failed to get status for job {job_id}. Err: {err}."
                )
            content = json.loads(content)
            operation_status = content.get("operation", {}).get("status", None)
            if operation_status is None:
                raise AnsibleError(f"Failed to get status for job {job_id}.")

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

    def _process_put_file(self, data: str) -> str:
        """ """
        file_zip, err = compress_file(data, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to compress file. Error: {err}.")

        file_base64, err = encode_base64(file_zip)
        if err:
            raise AnsibleError(f"Failed to encode file. Error: {err}.")

        file_base64 = file_base64.decode("utf-8")
        return file_base64

    def _process_fetch_file(self, data: str) -> str:
        """ """
        decoded_file, err = decode_base64(data.encode())
        if err:
            raise AnsibleError(f"Failed to decode file. Error: {err}.")

        file_content, err = extract_file(decoded_file, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to extract file. Error: {err}.")

        return file_content

    def _wrapper_put_file(self, file_content: str, out_path: str) -> str:
        """ """
        profile_content, err = render_put_file(
            out_path, file_content, self.filename_inside_zip
        )
        if err:
            raise AnsibleError(f"Failed to render put file profile. Error: {err}.")

        return profile_content

    def _wrapper_fetch_file(self, in_path: str) -> str:
        """ """
        profile_content, err = render_fetch_file(
            in_path, self.filename_inside_zip, self.max_file_size_fetch_file
        )
        if err:
            raise AnsibleError(f"Failed to render fetch file profile. Error: {err}.")

        return profile_content

    def _connect(self) -> ConnectionBase:
        """Ansible connection override function responsible to establish tunnel from local to host.
        The transportation method for ZPE Cloud is based on API requests, then the connect method
        only establish an authenticated session to be used later."""
        self._log_info("[connect override]")
        # check if session already exists
        if self._api_session is None:
            self._create_api_session()

        if self.host_serial_number is None or self.host_zpecloud_id is None:
            if self._play_context.remote_addr is None:
                raise AnsibleConnectionFailure(
                    "Remote serial number from host was not found."
                )

            self.host_serial_number = self._play_context.remote_addr

            device, err = self._api_session.fetch_device_by_serial_number(
                self.host_serial_number
            )
            if err:
                raise AnsibleConnectionFailure(
                    f"Failed to fetch host ID. Error: {err}."
                )

            host_id = device.get("id", None)
            if host_id is None:
                raise AnsibleConnectionFailure(
                    f"Failed to find host ID for serial number: {self.host_serial_number}."
                )

            self.host_zpecloud_id = host_id

        return self

    def exec_command(
        self, cmd: str, in_data: bytes = None, sudoable: bool = True
    ) -> Tuple[bool, str, str]:
        """Ansible connection override function responsible to execute commands on host.
        Commands created by Ansible will be wrapped on a script profile to be executed via ZPE Cloud.
        """
        super(Connection, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)
        self._log_info("[exec_command override]")

        cmd = to_text(cmd)

        # change default executable process to "su ansible". This enforce the commands to be executed as ansible user.
        # e.g.
        # From: /bin/sh -c 'echo ~ && sleep 0'
        # To: su ansible -c 'echo ~ && sleep 0' for default ansible user
        if self.become is None:
            if self._play_context.executable not in cmd:
                raise AnsibleError(
                    "Executable process in command does not match expected process."
                )

            cmd = cmd.replace(self._play_context.executable, "su ansible")

        profile_content = self._wrapper_exec_command(cmd)

        # create a profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # Apply profile to Nodegrid device
        job_id = self._apply_profile(self.host_zpecloud_id, profile_id)

        # Wait profile to finish
        job_output, err = self._wait_job_to_finish(job_id)
        if err:
            return (1, b"", to_bytes(err))

        # Delete profile from configuration list
        self._delete_profile(profile_id)

        return (0, to_bytes(job_output), b"")

    def put_file(self, in_path: str, out_path: str) -> None:
        """Ansible connection override function responsible to transfer file from local to host.
        Files are compressed, converted to base64, and then wrapped in script profile that is executed on
        host via ZPE Cloud.
        Once executed in the host, the script will decode, extract the files, and then write to host path.
        """
        super(Connection, self).put_file(in_path, out_path)
        self._log_info("[put_file override]")

        if not os.path.exists(to_bytes(in_path, errors="surrogate_or_strict")):
            raise AnsibleFileNotFound(
                f"File or module does not exist. Path: {in_path}."
            )

        file_stat = os.stat(to_bytes(in_path, errors="surrogate_or_strict"))
        if file_stat.st_size > self.max_file_size_put_file:
            raise AnsibleError(
                f"Size of file {in_path} is bigger than limit of {self.max_file_size_put_file} bytes."
            )

        file_content, err = read_file(in_path)
        if err:
            raise AnsibleError(f"Failed to read file. Path: {in_path}. Error: {err}.")

        # Zip file content and encode to base64
        file_content = self._process_put_file(file_content)

        profile_content = self._wrapper_put_file(file_content, out_path)

        # Create profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # Apply profile to Nodegrid device
        job_id = self._apply_profile(self.host_zpecloud_id, profile_id)

        # Wait profile to finish
        err = self._wait_job_to_finish(job_id)[1]
        if err:
            raise AnsibleError(f"File transfer failed. Error: {err}.")

        # Delete profile from configuration list
        self._delete_profile(profile_id)

    def fetch_file(self, in_path: str, out_path: str) -> None:
        """Ansible connection override function responsible to transfer file from host to local.
        A script profile is used to fetch file from host via ZPE Cloud.
        Once executed in the host, the script will read the file, compress it, convert to base64 and write to stdout.
        The stdout will be read by Ansible once the job is finished. The content of stdout will be decoded from base64,
        extracted, and then write to local path."""
        super(Connection, self).fetch_file(in_path, out_path)
        self._log_info("[fetch_file override]")

        profile_content = self._wrapper_fetch_file(in_path)

        # Create profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # Apply profile to Nodegrid device
        job_id = self._apply_profile(self.host_zpecloud_id, profile_id)

        # Wait profile to finish
        job_output, err = self._wait_job_to_finish(job_id)
        if err:
            raise AnsibleError(f"File transfer failed. Error: {err}.")

        self._delete_profile(profile_id)

        # Decode output from base64, and extract file from zip
        file_content = self._process_fetch_file(job_output)

        # write file to local
        err = write_file(out_path, file_content)[1]
        if err:
            raise AnsibleError(f"Failed to save file. Error: {err}.")

    def close(self) -> None:
        """Ansible connection override function responsible to close tunnel to host.
        A logout from ZPE Cloud API will be performed."""
        self._log_info("[close override]")
        if self._api_session:
            err = self._api_session.logout()[1]
            if err:
                self._log_warning(
                    f"Failed to close session from ZPE Cloud. Error: {err}"
                )

    def reset(self) -> None:
        """Ansible connection override function responsible to reset tunnel to host.
        A logout, followed by a login on ZPE Cloud API will be performed."""
        self._log_info("[reset override]")
        self.close()
        self._connect()
