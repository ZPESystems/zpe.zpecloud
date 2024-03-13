# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: software_upgrade
short_description: Apply software upgrade operations on Nodegrid device enrolled in ZPE Cloud.
description:
  - Apply software upgrade operation on Nodegrid devices enrolled in ZPE Cloud.
  - For software downgrade, it is necessary to set option allow_downgrade to True.
  - By default, module will fail if a device will be downgraded to prevent device from factory reset.
options:
  version:
    description:
      - Desired Nodegrid OS version for upgrade.
      - Nodegrid OS version follows pattern <major>.<minor>.<patch>
    type: str
    required: true
  allow_downgrade:
    description:
      - Flag to allow a device to be downgraded if target version is lower than current version.
      - This flag is disabled by default, and task will be skipped in case of downgrade.
      - Example of downgrade. upgrade to version 5.8.17 on a device running version 5.10.8.
    type: bool
    default: false
author:
  - Daniel Nesvera (@zpe-dnesvera)
notes:
  - Action will poll ZPE Cloud API to fetch status of software upgrade until status is successful.
  - The poll algorithm uses exponential backoff delay, and will timeout after 1 hour.
  - ZPE Cloud only applies profile to device that are enrolled, and status is online, or failover.
  - Task will fail with unreachable result if ZPE Cloud is not able to apply profile to device.
"""

EXAMPLES = r"""
# Software upgrade without allowing downgrade
- name: Software upgrade to NG OS v5.10.10
  zpe.zpecloud.software_upgrade:
    version: "5.10.10"

# Software upgrade allowing possible downgrade of devices
- name: Software upgrade to NG OS v5.8.15
  zpe.zpecloud.software_upgrade:
    version: "5.8.15"
    allow_downgrade: true
"""
