# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import os
import pytest
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

from ansible.errors import AnsibleParserError

from ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory import (
    InventoryModule,
)

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

@pytest.fixture(scope="module")
def inventory():
    inventory = InventoryModule()
    inventory.get_option = MagicMock()

    return inventory


""" Tests for verify_file """


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("zpecloud_foobar.yml", False), ("zpecloud.yml", True), ("zpecloud.yaml", True)],
)
def test_verify_file_wrong_filename(tmp_path, inventory, filename, expected):
    """Inventory without correct file name must fail verification."""
    file = tmp_path / f"{filename}"
    file.touch()
    assert inventory.verify_file(str(file)) is expected


""" Tests for verify_file """
""" Tests for _create_api_session """


@pytest.mark.parametrize(
    ("configuration"),
    [
        {"password": "mysecurepassword"},  # username missing
        {"username": "myuser@myemail.com"},  # password missing
    ],
)
def test_create_api_session_missing_required_configuration_raise_error(
    inventory, configuration
):
    """Execution without credentials must raise error."""
    _options = configuration

    def _get_option_side_effect(*args):
        return _options.get(*args)

    inventory.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleParserError):
        inventory._create_api_session()


@patch(
    "ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory.ZPECloudAPI"
)
def test_create_api_session_read_credentials_from_config_file(
    mock_zpe_cloud_api, inventory
):
    """Test reading configuration from config file via options."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)

    _options = {
        "username": "myuser@myemail.com",
        "password": "mysecurepassword",
        "organization": "My organization",
    }

    def _get_option_side_effect(*args):
        return _options.get(*args)

    inventory.get_option.side_effect = _get_option_side_effect

    inventory._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory.ZPECloudAPI"
)
def test_create_api_session_read_credentials_from_env_variable(
    mock_zpe_cloud_api, inventory
):
    """Test reading configuration from environment variables."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)
    inventory.get_option.return_value = None

    _options = {
        "ZPECLOUD_USERNAME": "myuser@myemail.com",
        "ZPECLOUD_PASSWORD": "mysecurepassword",
        "ZPECLOUD_ORGANIZATION": "My organization",
    }

    os.environ['ZPECLOUD_USERNAME'] = _options.get("ZPECLOUD_USERNAME")
    os.environ['ZPECLOUD_PASSWORD'] = _options.get("ZPECLOUD_PASSWORD")
    os.environ['ZPECLOUD_ORGANIZATION'] = _options.get("ZPECLOUD_ORGANIZATION")

    inventory._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("ZPECLOUD_USERNAME"), _options.get("ZPECLOUD_PASSWORD")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("ZPECLOUD_ORGANIZATION")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory.ZPECloudAPI"
)
def test_create_api_session_zpe_cloud_api_authentication_fail(
    mock_zpe_cloud_api, inventory
):
    """Failure while creating ZPECloudAPI instance."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = (
        "",
        "Authentication error",
    )

    _options = {"username": "myuser@myemail.com", "password": "mysecurepassword"}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    inventory.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleParserError):
        inventory._create_api_session()

    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )


@patch(
    "ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory.ZPECloudAPI"
)
def test_create_api_session_switch_organization_fail(mock_zpe_cloud_api, inventory):
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

    inventory.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleParserError):
        inventory._create_api_session()

    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )


""" Tests for _create_api_session """
