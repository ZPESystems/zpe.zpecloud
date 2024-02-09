#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from typing import Union, Tuple
import base64
import zipfile
from io import StringIO



def read_file(in_path: str) -> Union[Tuple[str, None], Tuple[None, str]]:
    try:
        with open(in_path, "r") as f:
            data = f.read()
        return data, None
    except Exception as err:
        return None, f"Failed to read file {in_path}. Error: {err}"

def write_file(out_path: str, data: str) -> Union[Tuple[bool, None], Tuple[None, str]]:
    try:
        with open(out_path, "w") as f:
            f.write(data)
        return True, None
    except Exception as err:
        return None, f"Failed to write file {out_path}. Error: {err}"

def encode_data(data: str):
    try:
        enc_data = base64.b64encode(data)

    except Exception as err:
        return None, f"Failed to encode data. Error: {err}"

    return enc_data, None


def decode_data(data: str):
    try:
        dec_data = base64.b64decode(data)
    except Exception as err:
        return None, f"Failed to decode data. Error: {err}"

    return dec_data, None

def zip_data(data: str):
    zipped_str = ""
    io_data = BytesIO(data)
    mem_zip = BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("blah.txt", data)
    #z = zipfile.ZipFile(zipped_data)
    #z.write(io_data, compress_type=zipfile.ZIP_DEFLATED)
    zipped_str = mem_zip.getvalue()

    return zipped_str, None


def unzip_data(data: str):
    blah = ""
    mem_zip = BytesIO(data)
    mem_file = ""
    with  zipfile.ZipFile(mem_zip, mode="r", compression=zipfile.ZIP_DEFLATED) as zf:
        with zf.open("blah.txt") as myfile:
            mem_file = myfile.read()

    return mem_file