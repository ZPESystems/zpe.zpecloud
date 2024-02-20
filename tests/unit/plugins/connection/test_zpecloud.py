# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch

from ansible.plugins.connection import ConnectionBase
from ansible.plugins.loader import connection_loader, become_loader
from ansible.playbook.play_context import PlayContext

from ansible.errors import (
    AnsibleAuthenticationFailure,
    AnsibleConnectionFailure,
    AnsibleError,
    AnsibleFileNotFound,
    AnsibleOptionsError
)


@pytest.fixture(scope="module")
def connection():
    pc = PlayContext()
    conn = connection_loader.get("zpe.zpecloud.zpecloud", pc, "/dev/null")
    conn.get_option = MagicMock()

    return conn


#### Overwritten methods

# _connect
# exec_command
# put_file
# fetch_file
# close
# reset


#### Other methods

""" Tests for _create_api_session """


@pytest.mark.parametrize(
    ("configuration"),
    [
        {"username": None, "password": "mysecurepassword"},
        {"username": "myuser@myemail.com", "password": None}
    ],
)
def test_create_api_session_missing_required_configuration_raise_error(configuration, connection):
    """Execution without credentials must raise error."""
    _options = configuration

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleConnectionFailure):
        connection._create_api_session()


""" Tests for _create_api_session """


# _create_api_session
# _wrapper_exec_command
# _create_profile
# _delete_profile
# _apply_profile
# _wait_job_to_finish
# _process_put_file
# _process_fetch_file
# _wrapper_put_file
# _wrapper_fetch_file


def test_missing_credentials():
    pass


def test_get_credentials_from_variables():
    pass


def test_get_credentials_from_env():
    pass


def test_run_task_offline_device_fails():
    pass


def test_wait_job_finish_timeout():
    pass


def test_wait_job_finish_succeed():
    pass
