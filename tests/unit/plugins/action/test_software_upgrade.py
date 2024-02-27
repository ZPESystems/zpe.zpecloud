# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import pytest
import sys
from unittest.mock import MagicMock, Mock
from unittest.mock import patch

from ansible.playbook.play_context import PlayContext

from ansible.errors import AnsibleConnectionFailure, AnsibleError, AnsibleFileNotFound

from ansible_collections.zpe.zpecloud.plugins.action.software_upgrade import ActionModule

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")


# Fixture for action module
@pytest.fixture(scope="module")
def action():
    pc = PlayContext()
    action = action(pc, "/dev/null")
    action.get_option = MagicMock()

    return action


# Overwritten methods
""" Tests for update_vars """


def test_store_variables_from_inventory(action):
    host_variables = {
        "hostname": "hostname123",
        "model": "NSR",
        "serial_number": "12345654321",
        "zpecloud_id": "50681",
    }

    action.update_vars(host_variables)

    assert action.host_serial_number == host_variables.get("serial_number")
    assert action.host_zpecloud_id == host_variables.get("zpecloud_id")


""" Tests for update_vars """
""" Tests for _connect """

""" Tests for _connect """
""" Tests for exec_command """

""" Tests for exec_command """
""" Tests for put_file """


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.zpecloud.actionBase.put_file"
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.os")
def test_put_file_file_not_exist(mock_os, mock_super_put_file, action):
    """Try to send a file to host that does not exist."""
    mock_os.path.exists.return_value = False

    mock_super_put_file.return_value = None

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleFileNotFound):
        action.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.zpecloud.actionBase.put_file"
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.os")
def test_put_file_size_too_big(mock_os, mock_super_put_file, action):
    """Try to send a file to host that is too big."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=action.max_file_size_put_file + 1)

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        action.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.read_file")
@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.zpecloud.actionBase.put_file"
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.os")
def test_put_file_fail_read_file(
    mock_os, mock_super_put_file, mock_read_file, action
):
    """Try to send a file to host but failed to read file."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=action.max_file_size_put_file)
    mock_read_file.return_value = (None, "some error")

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        action.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.read_file")
@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.zpecloud.actionBase.put_file"
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.os")
def test_put_file_fail_wait_job_finish(
    mock_os, mock_super_put_file, mock_read_file, action
):
    """Try to send a file to host but failed to wait for job."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=action.max_file_size_put_file)
    mock_read_file.return_value = ("somefilecontent", None)

    action._process_put_file = Mock()
    action._wrapper_put_file = Mock()
    action._create_profile = Mock()
    action._apply_profile = Mock()
    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = (None, "some error")

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        action.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1
    assert action._process_put_file.call_count == 1
    assert action._wrapper_put_file.call_count == 1
    assert action._create_profile.call_count == 1
    assert action._apply_profile.call_count == 1
    assert action._wait_job_to_finish.call_count == 1


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.read_file")
@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.zpecloud.actionBase.put_file"
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.os")
def test_put_file_success(mock_os, mock_super_put_file, mock_read_file, action):
    """Succeed to send file to host."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=action.max_file_size_put_file)
    mock_read_file.return_value = ("somefilecontent", None)

    action._process_put_file = Mock()
    action._wrapper_put_file = Mock()
    action._create_profile = Mock()
    action._apply_profile = Mock()
    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("someoutput", None)
    action._delete_profile = Mock()

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    action.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1
    assert action._process_put_file.call_count == 1
    assert action._wrapper_put_file.call_count == 1
    assert action._create_profile.call_count == 1
    assert action._apply_profile.call_count == 1
    assert action._wait_job_to_finish.call_count == 1
    assert action._delete_profile.call_count == 1


""" Tests for put_file """
""" Tests for fetch_file """

""" Tests for fetch_file """
""" Tests for close """


@pytest.mark.parametrize(
    ("session", "expected"),
    [
        (MagicMock(), True),
        (None, False),
    ],
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def close_action(mock_zpecloud_api, action, session, expected):
    """Test action is being closed."""
    action._api_session = MagicMock()
    mock_zpecloud_api.return_value.logout = MagicMock()
    mock_zpecloud_api.return_value.logout.return_value = ("", None)

    # TODO - pytest is return mock class instead of string
    """[WARNING]: ZPE Cloud action - Host ID: None - Host SN: None - Failed to
close session from ZPE Cloud. Error: <MagicMock
name='mock.logout().__getitem__()' id='139724302534640'>."""

    action.close()

    if expected:
        mock_zpecloud_api.return_value.logout.assert_called_once()


""" Tests for close """
""" Tests for reset """


def test_reset_action(action):
    """Test if reset calls close and connect again."""
    action.close = MagicMock()
    action.close.return_value = None
    action._connect = MagicMock()
    action._connect.return_value = None

    action.reset()

    action.close.assert_called_once()
    action._connect.assert_called_once()


""" Tests for reset """


# Other methods
""" Tests for _create_api_session """


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

    action.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleactionFailure):
        action._create_api_session()


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
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

    action.get_option.side_effect = _get_option_side_effect

    action._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(
        _options.get("organization")
    )


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_create_api_session_read_credentials_from_env_variable(
    mock_zpe_cloud_api, action
):
    """Test reading configuration from environment variables."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)
    action.get_option.return_value = None

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


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
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

    action.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleactionFailure):
        action._create_api_session()

    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(
        _options.get("username"), _options.get("password")
    )


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_create_api_session_switch_organization_fail(mock_zpe_cloud_api, action):
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

    action.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleactionFailure):
        action._create_api_session()

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


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_request_fail(mock_zpecloud_api, action):
    """Test wait job to finish but API request failed."""
    action._api_session = mock_zpecloud_api
    mock_zpecloud_api.get_job.return_value = (None, "Some error")

    with pytest.raises(AnsibleError):
        action._wait_job_to_finish("1234")


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_missing_status(mock_zpecloud_api, action):
    """API response is invalid."""
    action._api_session = mock_zpecloud_api
    mock_zpecloud_api.get_job.return_value = ("{}", None)

    with pytest.raises(AnsibleError):
        action._wait_job_to_finish("1234")


@pytest.mark.parametrize(
    ("job_status"),
    [("Cancelled"), ("Timeout"), ("Failed")],
)
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_fail(mock_zpecloud_api, action, job_status):
    """Test wait job to finish but job finished with some failure status."""
    action._api_session = mock_zpecloud_api

    response = json.dumps({"operation": {"status": job_status}})
    mock_zpecloud_api.get_job.return_value = (response, None)

    content, err = action._wait_job_to_finish("1234")

    assert content is None
    assert job_status in err


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.time")
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.requests")
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_success(
    mock_zpecloud_api, mock_requests, mock_time, action
):
    """Test wait job to finish with sequence of job status."""
    action._api_session = mock_zpecloud_api

    sending_status = json.dumps({"operation": {"status": "Sending"}, "output_file": ""})
    scheduled_status = json.dumps(
        {"operation": {"status": "Scheduled"}, "output_file": ""}
    )
    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})
    successful_status = json.dumps(
        {"operation": {"status": "Successful"}, "output_file": "someurl"}
    )

    mock_zpecloud_api.get_job = Mock()
    mock_zpecloud_api.get_job.side_effect = (
        [(sending_status, None)] * 2
        + [(scheduled_status, None)] * 2
        + [(started_status, None)] * 2
        + [(successful_status, None)]
    )

    job_output = "somethinginbase64"
    mock_requests.get.return_value = Mock(content=job_output)

    mock_time.time.return_value = 0
    mock_time.sleep.return_value = None

    content, err = action._wait_job_to_finish("12314")

    assert err is None
    assert content == job_output

    assert mock_zpecloud_api.get_job.call_count == 7
    assert mock_requests.get.call_count == 1
    assert mock_time.time.call_count == 8
    assert mock_time.sleep.call_count == 6


@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.time")
@patch("ansible_collections.zpe.zpecloud.plugins.action.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_ansible_timeout(
    mock_zpecloud_api, mock_time, action
):
    """Ansible will timeout after some time polling job status."""
    action._api_session = mock_zpecloud_api

    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})

    mock_zpecloud_api.get_job.return_value = (started_status, None)

    start_time = 1000  # seconds
    mock_time.time.side_effect = [
        start_time,  # start time
        start_time + 10,  # first iteration
        start_time + 1000,  # second iteration
        start_time
        + action.timeout_wait_job_finish,  # third iteration (equal to timeout)
        start_time + action.timeout_wait_job_finish + 1,  # timeout
    ]
    mock_time.sleep.return_value = None

    content, err = action._wait_job_to_finish("12314")

    assert content is None
    assert err == "Timeout"

    assert mock_zpecloud_api.get_job.call_count == 3
    assert mock_time.time.call_count == 5
    assert mock_time.sleep.call_count == 3


""" Tests for _wait_job_to_finish """
""" Tests for _process_put_file """

""" Tests for _process_put_file """
""" Tests for _process_fetch_file """

""" Tests for _process_fetch_file """
""" Tests for _wrapper_put_file """

""" Tests for _wrapper_put_file """
""" Tests for _wrapper_fetch_file """

""" Tests for _wrapper_fetch_file """
