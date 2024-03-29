#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from jinja2 import Environment, TemplateError
from typing import Dict

from ansible_collections.zpe.zpecloud.plugins.plugin_utils.types import StringError


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
from typing import Optional

filename = "{{ filename }}"
out_path = "{{ out_path }}"
compression_method = {{ compression_method }}


def decode_base64(data: bytes) -> Optional[bytes]:
    dec_data = b""
    try:
        dec_data = base64.b64decode(data)

    except Exception as err:
        print(f"Failed to decode file. Error: {err}")
        return None

    return dec_data


def extract_file(data: bytes, filename: str) -> Optional[bytes]:
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
    decoded_file = decode_base64(file_b64_str.encode())
    if decoded_file is None:
        exit(1)

    # extract file from compressed file
    extracted_file = extract_file(decoded_file, filename)
    if extracted_file is None:
        exit(1)

    with open(out_path, "wb") as f:
        f.write(extracted_file)

    uid = getpwnam("ansible").pw_uid
    gid = getpwnam("ansible").pw_gid
    os.chown(out_path, uid, gid)

"""

FETCH_FILE_TEMPLATE = """\
#!/usr/bin/env python3

import base64
import os
import zipfile

from io import BytesIO
from typing import Optional

filename = "{{ filename }}"
in_path = "{{ in_path }}"
compression_method = {{ compression_method }}
max_file_size = {{ max_file_size }}


def encode_base64(data: bytes) -> Optional[bytes]:
    enc_data = b""
    try:
        enc_data = base64.b64encode(data)

    except Exception as err:
        print(f"Failed to encode data. Error: {err}.")
        return None

    return enc_data


def compress_file(data: bytes, filename: str) -> Optional[bytes]:
    zipped_str = b""
    mem_zip = BytesIO()

    try:
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, data)
        zipped_str = mem_zip.getvalue()
    except Exception as err:
        print(f"Failed to compress file. Error: {err}.")
        return None

    return zipped_str


if __name__ == "__main__":
    data = ""

    if not os.path.exists(in_path):
        print(f"File {in_path} does not exist.")
        exit(1)

    file_stat = os.stat(in_path)
    if file_stat.st_size > max_file_size:
        print(f"Size of file {in_path} is bigger than limit of {max_file_size} bytes.")
        exit(1)

    try:
        with open(in_path, "rb") as f:
            data = f.read()

    except Exception as err:
        print(f"Failed to read file {in_path}. Error: {err}.")
        exit(1)

    # zip original file
    compressed_file = compress_file(data, filename)
    if compressed_file is None:
        exit(1)

    # bytes to base64
    encoded_file = encode_base64(compressed_file)
    if encoded_file is None:
        exit(1)

    # return data that will be used by Ansible
    print(encoded_file.decode("utf-8"))

"""


def _render_template(template: str, context: Dict) -> StringError:
    """Render specific template based on context dictionary."""
    try:
        jinja_env = Environment()
        jinja_template = jinja_env.from_string(template)
        render_template = jinja_template.render(context)
        return render_template, None
    except TemplateError as err:
        return None, f"Failed to render profile content. Err: {err}"


def render_exec_command(command: str) -> StringError:
    """Use jinja to render bash script profile with commands generated by Ansible."""
    context = {"command": command}
    return _render_template(EXEC_COMMAND_TEMPLATE, context)


def render_put_file(out_path: str, file_content: str, filename: str) -> StringError:
    """Use jinja to render python script profile needed to move files from local to host."""
    context = {
        "content": file_content,
        "out_path": out_path,
        "filename": filename,
        "compression_method": 8,
    }
    return _render_template(PUT_FILE_TEMPLATE, context)


def render_fetch_file(in_path: str, filename: str, max_file_size: int) -> StringError:
    """Use jinja to render python script profile needed to move files form host to local."""
    context = {
        "in_path": in_path,
        "filename": filename,
        "compression_method": 8,
        "max_file_size": max_file_size,
    }
    return _render_template(FETCH_FILE_TEMPLATE, context)
