#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish, this is required for contributions to Ansible
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from time import sleep

from ansible.plugins.action import ActionBase
from ansible.utils.display import Display


display = Display()

MINUTE = 60  # seconds


class ActionModule(ActionBase):
    """Action module used to apply software upgrade for Nodegrid devices over ZPE Cloud API."""

    TRANSFERS_FILES = False
    _VALID_ARGS = frozenset(("msg",))
    _requires_connection = False

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
        self.timeout_wait_job_finish = 60 * MINUTE  # seconds
        self.max_delay_wait_job_finish = 3 * MINUTE  # seconds

    def run(self, tmp=None, task_vars=None):
        action_module_args = self._task.args.copy()
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        msg = "Failed as requested from task"
        if self._task.args and "msg" in self._task.args:
            msg = self._task.args.get("msg")

        result["failed"] = True
        result["msg"] = msg
        return result
