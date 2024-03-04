# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import pytest
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

from ansible.playbook.play_context import PlayContext

from ansible.errors import AnsibleActionFail

from ansible_collections.zpe.zpecloud.plugins.action.software_upgrade import (
    ActionModule,
)

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")


# Fixture for action module
@pytest.fixture(scope="module")
def action():
    pc = PlayContext()
    connection = MagicMock()
    loader = MagicMock()
    templar = MagicMock()
    shared_loader_obj = MagicMock()
    task = MagicMock()
    action = ActionModule(
        play_context=pc,
        loader=loader,
        templar=templar,
        shared_loader_obj=shared_loader_obj,
        task=task,
        connection=connection,
    )
    action._connection = MagicMock()

    return action


""" Tests for _create_api_session """


def test_create_api_session_missing_connection_options(action):
    """Action plugin was not able to get options from connection."""
    action._connection = None

    with pytest.raises(AnsibleActionFail):
        action._create_api_session()


@pytest.mark.parametrize(
    ("configuration"),
    [
        {"username": None, "password": "mysecurepassword"},
        {"username": "myuser@myemail.com", "password": None},
    ],
)
def test_create_api_session_missing_required_configuration_raise_error(
    configuration, action
):
    """Playbook without credentials on variables, neither on env, must raise error."""
    _options = configuration

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleActionFail):
        action._create_api_session()


@patch(
    "ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_action_base.ZPECloudAPI"
)
def test_create_api_session_read_credentials_from_playbook_vars(
    mock_zpe_cloud_api, action
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

    action._connection.get_option.side_effect = _get_option_side_effect

    action._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_action_base.ZPECloudAPI"
)
def test_create_api_session_read_credentials_from_env_variable(
    mock_zpe_cloud_api, action
):
    """Test reading configuration from environment variables."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)
    action._connection.get_option.return_value = None

    _options = {
        "ZPECLOUD_USERNAME": "myuser@myemail.com",
        "ZPECLOUD_PASSWORD": "mysecurepassword",
        "ZPECLOUD_ORGANIZATION": "My organization",
    }

    os.environ["ZPECLOUD_USERNAME"] = _options.get("ZPECLOUD_USERNAME")
    os.environ["ZPECLOUD_PASSWORD"] = _options.get("ZPECLOUD_PASSWORD")
    os.environ["ZPECLOUD_ORGANIZATION"] = _options.get("ZPECLOUD_ORGANIZATION")

    action._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("ZPECLOUD_USERNAME"), _options.get("ZPECLOUD_PASSWORD")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("ZPECLOUD_ORGANIZATION")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_action_base.ZPECloudAPI"
)
def test_create_api_session_zpe_cloud_api_authentication_fail(
    mock_zpe_cloud_api, action
):
    """Failure while creating ZPECloudAPI instance."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = (
        "",
        "Authentication error",
    )

    _options = {"username": "myuser@myemail.com", "password": "mysecurepassword"}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleActionFail):
        action._create_api_session()

    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.plugin_utils.zpecloud_action_base.ZPECloudAPI"
)
def create_api_session_switch_organization_fail(mock_zpe_cloud_api, action):
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

    action._connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleActionFail):
        action._create_api_session()

    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )


""" Tests for _create_api_session """
