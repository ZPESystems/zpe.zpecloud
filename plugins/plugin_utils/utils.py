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
from io import BytesIO

# todo - check if compression algorithm is supported


def read_file(in_path: str) -> Union[Tuple[str, None], Tuple[None, str]]:
    data = b""
    try:
        with open(in_path, "rb") as f:
            data = f.read()
        return data, None
    except Exception as err:
        return None, f"Failed to read file {in_path}. Error: {err}"


def write_file(out_path: str, data: str) -> Union[Tuple[bool, None], Tuple[None, str]]:
    try:
        with open(out_path, "wb") as f:
            f.write(data)
        return True, None
    except Exception as err:
        return None, f"Failed to write file {out_path}. Error: {err}"


# TODO - verify types
def encode_base64(data: bytes) -> Union[Tuple[bytes, None], Tuple[None, str]]:
    enc_data = b""
    try:
        enc_data = base64.b64encode(data)

    except Exception as err:
        return None, f"Failed to encode data. Error: {err}"

    return enc_data, None


def decode_base64(data: bytes) -> Union[Tuple[bool, None], Tuple[None, str]]:
    dec_data = b""
    try:
        dec_data = base64.b64decode(data)
    except Exception as err:
        return None, f"Failed to decode data. Error: {err}"

    return dec_data, None


def compress_file(
    data: str, filename: str
) -> Union[Tuple[bool, None], Tuple[None, str]]:
    zipped_str = b""
    mem_zip = BytesIO()
    # TODO - get algorithm from flag zipfile.ZIP_DEFLATED and check which should be used based on user's computer
    # TODO - validation for errors
    try:
        with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(filename, data)
        zipped_str = mem_zip.getvalue()
    except Exception as err:
        return None, f"Failed do compress data. Error: {err}"

    return zipped_str, None


def extract_file(
    data: str, filename: str
) -> Union[Tuple[bool, None], Tuple[None, str]]:
    mem_zip = BytesIO(data)
    mem_file = b""
    try:
        with zipfile.ZipFile(mem_zip, mode="r", compression=zipfile.ZIP_DEFLATED) as zf:
            with zf.open(filename) as myfile:
                mem_file = myfile.read()
    except Exception as err:
        return None, f"Failed to extract data. Error: {err}"

    return mem_file, None


def exponential_backoff_delay(attempt: int, max_delay: int) -> int:
    """Generate delay period based on exponential backoff algorithm
    attempt: Current amount of attempts.
    max_delay: Max delay time in seconds.
    return: Delay based on number of attempts, or max delay."""
    if attempt <= 0:
        return 1

    return min(2 ** (attempt - 1), max_delay)
