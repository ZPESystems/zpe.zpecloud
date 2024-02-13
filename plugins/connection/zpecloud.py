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
import requests
import time
import uuid


from datetime import datetime
from typing import Tuple, Union
from io import StringIO

from ansible import constants as C
from ansible.errors import (
    AnsibleAuthenticationFailure,
    AnsibleConnectionFailure,
    AnsibleError,
    AnsibleFileNotFound,
    AnsibleOptionsError
)
from ansible.compat import selectors
from ansible.module_utils.six import PY3, text_type, binary_type
from ansible.module_utils.six.moves import shlex_quote
from ansible.module_utils._text import to_bytes, to_text
from ansible.module_utils.parsing.convert_bool import BOOLEANS, boolean
from ansible.plugins.connection import ConnectionBase, BUFSIZE
from ansible.plugins.shell.powershell import _parse_clixml
from ansible.utils.display import Display
from ansible.utils.path import unfrackpath, makedirs_safe

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import ZPECloudAPI
from ansible_collections.zpe.zpecloud.plugins.plugin_utils.jinja_templates import (
    render_exec_command,
    render_put_file,
    render_fetch_file
)

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.utils import (
    read_file,
    write_file,
    encode_base64,
    decode_base64,
    compress_file,
    extract_file
)

display = Display()


class Connection(ConnectionBase):
    """Plugin for connecting to Nodegrid device over ZPE CLOUD API"""

    transport = 'zpe.zpecloud.zpecloud'
    has_pipelining = True
    filename_inside_zip = "original-file"
    # TODO - what this means?

    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        display.vvvv("[zpecloud connection - __init__ override]")
        self._api_session = None
        self.host_zpecloud_id = None

    # TODO - create log function that indicates the serialnumber, and job
    # TODO - probably bug, if execute job in multiple devices, sometimes output is not loaded

    def update_vars(self, variables) -> None:
        """ """
        display.vvvv("[zpecloud connection - update_vars override]")
        self.host_serial_number = variables.get("serial_number", None)
        self.host_zpecloud_id = variables.get("zpecloud_id", None)

    def _create_api_session(self) -> None:
        """ """
        url = self.get_option("url", None) or os.environ.get("ZPECLOUD_URL", None)

        # default for url
        if url is None:
            url = "https://zpecloud.com"

        username = self.get_option("username", None) or os.environ.get("ZPECLOUD_USERNAME", None)
        if username is None:
            raise AnsibleConnectionFailure("Could not retrieve ZPE Cloud username from plugin configuration or environment.")

        password = self.get_option("password", None) or os.environ.get("ZPECLOUD_PASSWORD", None)
        if password is None:
            raise AnsibleConnectionFailure("Could not retrieve ZPE Cloud password from plugin configuration or environment.")

        organization = self.get_option("organization", None) or os.environ.get("ZPECLOUD_ORGANIZATION", None)

        try:
            self._api_session = ZPECloudAPI(url)
        except Exception as err:
            raise AnsibleConnectionFailure(f"Failed to authenticate on ZPE Cloud. Error: {err}.")

        result, err = self._api_session.authenticate_with_password(username, password)
        if err:
            raise AnsibleConnectionFailure(f"Failed to authenticate on ZPE Cloud. Error: {err}.")

        if organization:
            result, err = self._api_session.change_organization(organization)
            if err:
                raise AnsibleConnectionFailure(f"Failed to switch organization. Error: {err}.")

    def _wrapper_exec_command(self, cmd: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        profile_content, err = render_exec_command(cmd)
        if err:
            raise AnsibleError(f"Failed to execute command. Error: {err}.")

        return profile_content

    def _create_profile(self, profile_content: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        profile_name = f"ansible_{uuid.uuid4()}"
        display.v(f"Creating profile: {profile_name}")

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
                ("file", (profile_name, f)))

            response, error = self._api_session.create_profile(payload_file)

        except Exception as err:
            error = err

        finally:
            if f:
                f.close()

        if error:
            raise AnsibleError(f"Failed to create script profile in ZPE Cloud. Error: {error}.")

        profile_id = response.get("id", None)
        if profile_id is None:
            raise AnsibleError("Failed to retrieve ID from script profile.")

        return response.get("id")

    def _delete_profile(self, profile_id: str) -> None:
        """ """
        err = self._api_session.delete_profile(profile_id)[1]
        if err:
            display.warning(f"Failed to delete profile from ZPE Cloud. ID: {profile_id}. Error: {err}.")

    def _apply_profile(self, device_id: str, profile_id: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        display.v(f"Applying profile {profile_id} to device: {device_id}.")

        schedule = datetime.utcnow()
        content, err = self._api_session.apply_profile(device_id, profile_id, schedule)
        if err:
            raise AnsibleError(f"Failed to apply script profile to device. Error: {err}.")
        # TODO - show job uuid and serialnumber

        resp = json.loads(content)
        job_id = resp.get("job_id")

        return job_id

    def _wait_job_to_finish(self, job_id: str) -> Tuple[bool, str, str]:
        """ """
        # TODO - add a timeout for waiting finish
        while True:
            display.v(f"Checking job status for {job_id}.")

            content, err = self._api_session.get_job(job_id)
            if err:
                raise AnsibleError(f"Failed to get status for job {job_id}. Err: {err}.")

            content = json.loads(content)
            operation_status = content.get("operation", {}).get("status")
            operation_output_file_url = content.get("output_file", None)

            if operation_status == "Successful" and operation_output_file_url and len(operation_output_file_url) > 0:
                display.v(f"Job {job_id} finished successfully.")
                r = requests.get(operation_output_file_url)

                if isinstance(r.content, bytes):
                    return r.content.decode("utf-8"), None
                else:
                    return r.content, None

            elif operation_status == "Failed" or operation_status == "Cancelled" or operation_status == "Timeout":
                display.v(f"Job {job_id} failed.")
                r = requests.get(operation_output_file_url)
                return None, r.content

            time.sleep(1)

        # TODO - timeout
        raise AnsibleError(f"Timeout waiting feedback for job {job_id}.")

    def _process_put_file(self, data: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        file_zip, err = compress_file(data, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to compress file. Error: {err}.")

        file_base64, err = encode_base64(file_zip)
        if err:
            raise AnsibleError(f"Failed to encode file. Error: {err}.")

        file_base64 = file_base64.decode("utf-8")
        return file_base64

    def _process_fetch_file(self, data: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        decoded_file, err = decode_base64(data.encode())
        if err:
            raise AnsibleError(f"Failed to decode file. Error: {err}.")

        file_content, err = extract_file(decoded_file, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to extract file. Error: {err}.")

        return file_content

    def _wrapper_put_file(self, file_content: str, out_path: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        profile_content, err = render_put_file(out_path, file_content, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to render put file profile. Error: {err}.")

        return profile_content

    def _wrapper_fetch_file(self, in_path: str) -> Union[Tuple[str, None], Tuple[None, str]]:
        """ """
        profile_content, err = render_fetch_file(in_path, self.filename_inside_zip)
        if err:
            raise AnsibleError(f"Failed to render fetch file profile. Error: {err}.")

        return profile_content

    def _connect(self):
        """  """
        display.vvvv("[zpecloud connection - connect override]")
        # check if session already exists
        if self._api_session is None:
            self._create_api_session()
        return self

    def exec_command(self, cmd: str, in_data: bytes = None, sudoable: bool = True):
        """  """
        super(Connection, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)
        display.vvvv("[zpecloud connection - exec_command override]")

        cmd = to_text(cmd)

        # TODO - check if is possible to get the runner
        if "/bin/sh" in cmd:
            cmd = cmd.replace("/bin/sh", "su ansible")

        display.v("Patched cmd")
        display.v(f"{cmd}")

        # TODO - test wrapped profile

        profile_content = self._wrapper_exec_command(cmd)

        # create a profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # Apply profile to Nodegrid device
        job_id = self._apply_profile(self.host_zpecloud_id, profile_id)

        # Wait profile to finish
        job_output, err = self._wait_job_to_finish(job_id)
        if err:
            return (1, b'', to_bytes(err))

        # Delete profile from configuration list
        self._delete_profile(profile_id)

        return (0, to_bytes(job_output), b'')

    def put_file(self, in_path, out_path):
        """transfer a file from local to remote"""
        super(Connection, self).put_file(in_path, out_path)
        display.vvvv("[zpecloud connection - put_file override]")
        display.v("------> in path: ")
        display.v(in_path)
        display.v("------> out path: ")
        display.v(out_path)

        if not os.path.exists(to_bytes(in_path, errors="surrogate_or_strict")):
            raise AnsibleFileNotFound(f"File or module does not exist. Path: {in_path}.")

        file_content, err = read_file(in_path)
        if err:
            raise AnsibleError(f"Failed to read file. Path: {in_path}. Error: {err}.")

        # Zip file content and encode to base64
        file_content = self._process_put_file(file_content)

        profile_content = self._wrapper_put_file(file_content, out_path)

        # TODO - test wrapped profile

        # Create profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # TODO - check err or error

        # Apply profile to Nodegrid device
        job_id = self._apply_profile(self.host_zpecloud_id, profile_id)

        # Wait profile to finish
        err = self._wait_job_to_finish(job_id)[1]
        if err:
            raise AnsibleError(f"File transfer failed. Error: {err}.")

        # Delete profile from configuration list
        self._delete_profile(profile_id)

    def fetch_file(self, in_path, out_path):
        """ """
        super(Connection, self).fetch_file(in_path, out_path)
        display.vvvv("[zpecloud connection - fetch_file override]")

        display.v("------> in path: ")
        display.v(in_path)
        display.v("------> out path: ")
        display.v(out_path)

        profile_content = self._wrapper_fetch_file(in_path)

        # Create profile in ZPE Cloud
        profile_id = self._create_profile(profile_content)

        # TODO - check err or error

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

    def close(self):
        """  """
        display.vvvv("[zpecloud connection - close override]")
        if self._api_session:
            err = self._api_session.logout()[1]
            if err:
                display.warning("Failed to close session from ZPE Cloud. Error: {err}.")
        pass

    def reset(self):
        """Reset the connection."""
        display.vvvv("[zpecloud connection - reset override]")
        self.close()
        self._connect()
