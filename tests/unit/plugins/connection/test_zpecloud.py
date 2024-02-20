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
    AnsibleOptionsError,
)

from ansible_collections.zpe.zpecloud.plugins.connection.zpecloud import Connection


# Fixture for connection plugin
@pytest.fixture(scope="module")
def connection():
    pc = PlayContext()
    conn = Connection(pc, "/dev/null")
    conn.get_option = MagicMock()

    return conn


#### Overwritten methods
""" Tests for update_vars """

def test_store_variables_from_inventory(connection):
    host_variables = {
        "hostname": "hostname123",
        "model": "NSR",
        "serial_number": "12345654321",
        "zpecloud_id": "50681"
    }

    connection.update_vars(host_variables)

    assert connection.host_serial_number == host_variables.get("serial_number")
    assert connection.host_zpecloud_id == host_variables.get("zpecloud_id")

""" Tests for update_vars """
""" Tests for _connect """

""" Tests for _connect """
""" Tests for exec_command """

""" Tests for exec_command """
""" Tests for put_file """

""" Tests for put_file """
""" Tests for fetch_file """

""" Tests for fetch_file """
""" Tests for close """

""" Tests for close """
""" Tests for reset """

""" Tests for reset """


#### Other methods
""" Tests for _create_api_session """

@pytest.mark.parametrize(
    ("configuration"),
    [
        {"username": None, "password": "mysecurepassword"},
        {"username": "myuser@myemail.com", "password": None},
    ],
)
def test_create_api_session_missing_required_configuration_raise_error(
    configuration, connection
):
    """Playbook without credentials on variables, neither on env, must raise error."""
    _options = configuration

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleConnectionFailure):
        connection._create_api_session()


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_read_credentials_from_playbook_vars(
    mock_zpe_cloud_api, connection
):
    """Test reading configuration from playbook variables.
    Username, password, and organization are defined on playbook.
    """
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)

    _options = {
        "username": "myuser@myemail.com",
        "password": "mysecurepassword",
        "organization": "My organization",
    }

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    connection._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )

@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_read_credentials_from_env_variable(
    mock_zpe_cloud_api, connection
):
    """Test reading configuration from environment variables."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)
    connection.get_option.return_value = None

    _options = {
        "ZPECLOUD_USERNAME": "myuser@myemail.com",
        "ZPECLOUD_PASSWORD": "mysecurepassword",
        "ZPECLOUD_ORGANIZATION": "My organization",
    }

    os.environ['ZPECLOUD_USERNAME'] = _options.get("ZPECLOUD_USERNAME")
    os.environ['ZPECLOUD_PASSWORD'] = _options.get("ZPECLOUD_PASSWORD")
    os.environ['ZPECLOUD_ORGANIZATION'] = _options.get("ZPECLOUD_ORGANIZATION")

    connection._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("ZPECLOUD_USERNAME"), _options.get("ZPECLOUD_PASSWORD")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("ZPECLOUD_ORGANIZATION")
    )

@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_zpe_cloud_api_authentication_fail(
    mock_zpe_cloud_api, connection
):
    """Failure while creating ZPECloudAPI instance."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = (
        "",
        "Authentication error",
    )

    _options = {"username": "myuser@myemail.com", "password": "mysecurepassword"}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleConnectionFailure):
        connection._create_api_session()

    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_switch_organization_fail(mock_zpe_cloud_api, connection):
    """Failure while performing call to switch organization."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (
        False,
        "Failure",
    )

    _options = {
        "username": "myuser@myemail.com",
        "password": "mysecurepassword",
        "organization": "New organization",
    }

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleConnectionFailure):
        connection._create_api_session()

    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )

""" Tests for _create_api_session """
""" Tests for _wrapper_exec_command """

""" Tests for _wrapper_exec_command """
""" Tests for _create_profile """

""" Tests for _create_profile """
""" Tests for _delete_profile """

""" Tests for _delete_profile """
""" Tests for _apply_profile """

""" Tests for _apply_profile """
""" Tests for _wait_job_to_finish """

""" Tests for _wait_job_to_finish """
""" Tests for _process_put_file """

""" Tests for _process_put_file """
""" Tests for _process_fetch_file """

""" Tests for _process_fetch_file """
""" Tests for _wrapper_put_file """

""" Tests for _wrapper_put_file """
""" Tests for _wrapper_fetch_file """

""" Tests for _wrapper_fetch_file """

