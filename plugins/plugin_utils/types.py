#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from typing import List, Dict, Union, Tuple, Any

StringError = Union[Tuple[str, None], Tuple[Any, str]]
BytesError = Union[Tuple[bytes, None], Tuple[Any, str]]
BooleanError = Union[Tuple[bool, None], Tuple[bool, str]]
DictError = Union[Tuple[Dict, None], Tuple[None, str]]
ListDictError = Union[Tuple[List[Dict], None], Tuple[None, str]]
