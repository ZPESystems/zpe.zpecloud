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
  - This plugin performs the following.
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
# example vars.yml
---
ansible_connection: zpecloud
ansible_zpecloud_url: https://zpecloud.com
ansible_zpecloud_username: myuser@myemail.com
ansible_zpecloud_password: mysecurepassword
ansible_zpecloud_organization: "My oganization"

# example playbook_nodegrid.yml
---
- name: Test ZPE Cloud Connection Plugin for Nodegrid device
  hosts: zpecloud_device_online
  tasks:
    - command: whoami
"""

import errno
import fcntl
import hashlib
import os
import pty
import re
import subprocess
import time

from functools import wraps
from ansible import constants as C
from ansible.errors import (
    AnsibleAuthenticationFailure,
    AnsibleConnectionFailure,
    AnsibleError,
    AnsibleFileNotFound,
)
from ansible.errors import AnsibleOptionsError
from ansible.compat import selectors
from ansible.module_utils.six import PY3, text_type, binary_type
from ansible.module_utils.six.moves import shlex_quote
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.module_utils.parsing.convert_bool import BOOLEANS, boolean
from ansible.plugins.connection import ConnectionBase, BUFSIZE
from ansible.plugins.shell.powershell import _parse_clixml
from ansible.utils.display import Display
from ansible.utils.path import unfrackpath, makedirs_safe

import requests
import json
import uuid
import time
from datetime import datetime, timedelta

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_api import ZPECloudAPI

display = Display()

class Connection(ConnectionBase):
    ''' custom connections '''

    transport = 'custom_connection_for_me'

    # zpe cloud methods
    def authenticate(self):
        display.v("------> 2 _connect")
        ##do Rest API call for authentication
        self.zpe_cloud_session = requests.Session()

        # authentication
        # test
        payload = {
            "email": "user",
            "password": "pass"
        }

        r = self.zpe_cloud_session.post(f"{self.url}/user/auth", data=payload)
        display.v(f"------ _connect - Auth: {r.status_code}")
        pass

    def create_profile(self, file_path):
        self.profile_name = f"ansible_{uuid.uuid4()}"
        profile_filename = f"{self.profile_name}.sh"
        display.v(f"Creating profile: {self.profile_name}")

        with open(file_path, "rb") as f:
            payload_file=(
                ("name", (None, self.profile_name)),
                ("description", (None, "blah")),
                ("type", (None, "SCRIPT")),
                ("default", (None, "false")),
                ("is_apply_on_connect", (None, "false")),
                ("password_protected", (None, "false")),
                ("custom_command_name", (None, "")),
                ("is_custom_command_enabled", (None, "false")),
                ("language", (None, "SHELL")),
                ("dynamic", (None, "false")),
                ("file", (self.profile_name, f))
            )
            r = self.zpe_cloud_session.post(f"{self.url}/profile", files=payload_file)

        display.v("===================")
        display.v(f"---> create_profile: {r.status_code}")
        display.v(str(vars(r)))
        resp=json.loads(r.text)
        self.profile_id=resp.get("id")

    def apply_profile(self):
        device_id="4741"
        if self.host == "192.168.13.101":
            device_id="4741"
        elif self.host == "192.168.13.37":
            device_id="4742"
        elif self.host == "192.168.7.43":
            device_id="5068"

        display.v(f"-----> apply profile to device: {device_id}")

        apply_profile_url=f"{self.url}/profile/{self.profile_id}/device/{device_id}"

        schedule = datetime.utcnow() # + timedelta(seconds=10)
        display.v(f"----> schedule: {schedule}")

        payload = {
            "schedule": schedule.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "is_first_connection": "false"
        }

        display.v(f"----> payload: {payload}")

        display.v(f"Apply profile {self.profile_name} to device {device_id}")
        # apply profile to devir = self.zpe_cloud_session.post(apply_profile_url, data=payload)
        r = self.zpe_cloud_session.post(apply_profile_url, data=payload)
        display.v(str(vars(r)))
        resp=json.loads(r.text)
        job_id=resp.get("job_id")

        display.v(f"Request: {r.status_code}")
        display.v(f"Job id: {job_id}")

        time.sleep(5)

        # Check job execution
        display.v(f"Checking job status for {job_id}")
        operation_url=f"{self.url}/job/{job_id}/details?jobId={job_id}"

        while True:
            r = self.zpe_cloud_session.get(operation_url)
            resp=json.loads(r.text)

            operation_config_name=resp.get("operation",{}).get("configurationName")
            operation_status=resp.get("operation",{}).get("status")
            operation_output_file_url=resp.get("output_file", None)

            display.v(f"Operation name: {operation_config_name}")
            display.v(f"Operation status: {operation_status}")

            if operation_status == "Successful" and operation_output_file_url and len(operation_output_file_url) > 0:
                display.v(f"Job finished")
                display.v(f"Get content from: {operation_output_file_url}")
                r = requests.get(operation_output_file_url)

                display.v(str(r.content))
                return r.content

            elif operation_status == "Failed":
                display.v(f"Job failed")
                break

            time.sleep(10)


    # external methods
    def __init__(self, *args, **kwargs):
        super(Connection, self).__init__(*args, **kwargs)
        display.v("------> 1__init__")
        display.v("------> self content: ")
        display.v(str(vars(self._play_context)))

        self.host = self._play_context.remote_addr
        display.v(f"------> host: {self.host}")
        self.zpe_cloud_session = None
        self.profile_id = None
        self.profile_name = None
        self.url = "https://api.test-zpecloud.com"
        self.authenticate()

    def _connect(self):
        return self

    def exec_command(self, cmd, in_data=None, sudoable=True):
        super(Connection, self).exec_command(cmd, in_data=in_data, sudoable=sudoable)
        display.v("------> 3 exec_command")
        ##do Rest API call for execute command

        display.v("-----> exec_command - cmd: ")
        display.v(cmd)

        if "~ansible" in cmd:
            return(0, b'/home/ansible\n', b'')

        elif "umask" in cmd:
            key = re.search("echo ansible-tmp.*=", cmd)
            key = key.group()
            key = key.split()[1]
            value = re.search("/home/ansible/.*`\"", cmd)
            value = value.group()
            value = value.split()[0]
            stdout = str.encode(key + value + "\n")
            return(0, stdout, '')

        elif "chmod" in cmd:
            return(0, b'', b'')

        elif "rm -rf" in cmd:
            return(0, b'', b'')

        elif "python3" in cmd:
            display.v("----> apply profile to device")
            cmd_output = self.apply_profile()
            display.v("stdout: ")
            display.v(str(cmd_output))
            #b'\r\n{"cmd": "uptime -p", "stdout": "up 2 weeks, 5 days, 7 hours, 53 minutes", "stderr": "", "rc": 0, "start": "2023-12-04 02:25:26.643370", "end": "2023-12-04 02:25:26.650847", "delta": "0:00:00.007477", "changed": true, "invocation": {"module_args": {"_raw_params": "uptime -p", "_uses_shell": true, "warn": true, "stdin_add_newline": true, "strip_empty_ends": true, "argv": null, "chdir": null, "executable": null, "creates": null, "removes": null, "stdin": null}}}\r\n'

            #b'\n{"cmd": "uptime -p", "stdout": "up 2 weeks, 5 days, 7 hours, 58 minutes", "stderr": "", "rc": 0, "start": "2023-12-04 02:30:04.025577", "end": "2023-12-04 02:30:04.033460", "delta": "0:00:00.007883", "changed": true, "invocation": {"module_args": {"_raw_params": "uptime -p", "_uses_shell": true, "warn": true, "stdin_add_newline": true, "strip_empty_ends": true, "argv": null, "chdir": null, "executable": null, "creates": null, "removes": null, "stdin": null}}}\n'
            return (0, cmd_output, b'')

        else:
            display.v("----> skip command")
            return (0, b'', b'')

    def put_file(self, in_path, out_path):
        super(Connection, self).put_file(in_path, out_path)
        display.v("------> 4 put_file")
        ##do Rest API call for upload file
        display.v("------> in path: ")
        display.v(in_path)
        display.v("------> out path: ")
        display.v(out_path)
        self.create_profile(in_path)
        pass

    def fetch_file(self, in_path, out_path):
        super(Connection, self).fetch_file(in_path, out_path)
        display.v("------> 5 fetch_file")
        ##do Rest API call for download file
        pass

    def close(self):
        display.v("------> 6 close")
        ##close http connection
        pass

    def reset(self):
        """Reset the connection."""
        display.v("------> 7 reset")
        self.close()
        self._connect()