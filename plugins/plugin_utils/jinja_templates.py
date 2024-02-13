#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from jinja2 import (
    Environment,
    TemplateError
)
from typing import Dict, Union, Tuple

EXEC_COMMAND_TEMPLATE = """\
#!/bin/bash

{{ command }}

"""

PUT_FILE_TEMPLATE = """\
#!/usr/bin/env python3

import base64
import os
import zipfile

from io import BytesIO
from pwd import getpwnam
from typing import Union

filename = "{{ filename }}"
out_path = "{{ out_path }}"
compression_method = {{ compression_method }}


def decode_file(data: bytes) -> Union[bytes, None]:
    dec_data = b""
    try:
        dec_data = base64.b64decode(data)

    except Exception as err:
        print(f"Failed to decode file. Error: {err}")
        return None

    return dec_data


def extract_data(data: bytes, filename: str) -> Union[bytes, None]:
    mem_zip = BytesIO(data)
    mem_file = b""

    try:
        with zipfile.ZipFile(mem_zip, mode="r", compression=compression_method) as zf:
            with zf.open(filename) as myfile:
                mem_file = myfile.read()
    except Exception as err:
        print(f"failed to extract file. Error: {err}")
        return None

    return mem_file


if __name__ == "__main__":
    file_b64_str = "{{ content }}"

    # b64 string to bytes
    decoded_file = decode_file(file_b64_str.encode())
    if decoded_file is None:
        exit(1)

    # extract file from compressed file
    extracted_file = extract_data(decoded_file, filename)
    if extracted_file is None:
        exit(1)

    with open(out_path, "wb") as f:
        f.write(extracted_file)

    uid = getpwnam("ansible").pw_uid
    gid = getpwnam("ansible").pw_gid
    os.chown(out_path, uid, gid)

"""

FETCH_FILE_TEMPLATE = """\
#!/bin/bash

{{ command }}

"""

def _render_template(template: str, context: Dict) -> Union[Tuple[str, None], Tuple[None, str]]:
    """Render specific template based on context dictionary."""
    try:
        jinja_env = Environment()
        jinja_template = jinja_env.from_string(template)
        render_template = jinja_template.render(context)
        return render_template, None
    except TemplateError as err:
        return None, f"Failed to render profile content. Err: {err}"

def render_exec_command(command: str) -> Union[Tuple[str, None], Tuple[None, str]]:
    """Use jinja to render bash script profile with commands generated by Ansible."""
    context = {
        "command": command
    }
    return _render_template(EXEC_COMMAND_TEMPLATE, context)

def render_put_file(out_path: str, file_content: str, filename: str) -> Union[Tuple[str, None], Tuple[None, str]]:
    """Use jinja to render python script profile needed to move files from local to host."""
    context = {
        "content": file_content,
        "out_path": out_path,
        "filename": filename,
        "compression_method": 8
    }
    return _render_template(PUT_FILE_TEMPLATE, context)

def render_fetch_file(context: Dict) -> Union[Tuple[str, None], Tuple[None, str]]:
    """Use jinja to render python script profile needed to move files form host to local."""
    return _render_template(FETCH_FILE_TEMPLATE, context)