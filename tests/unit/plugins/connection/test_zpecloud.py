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

from ansible_collections.zpe.zpecloud.plugins.connection.zpecloud import Connection

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")


# Fixture for connection plugin
@pytest.fixture(scope="module")
def connection():
    pc = PlayContext()
    conn = Connection(pc, "/dev/null")
    conn.get_option = MagicMock()

    return conn


# Overwritten methods
""" Tests for _connect """


def test_connect_empty_remote_address(connection):
    """Empty remote address must raise error since it is not possible to know target device."""
    connection._api_session = Mock()
    connection.host_serial_number = None
    connection.host_zpecloud_id = None
    connection._play_context = Mock(remote_addr=None)
    connection.become = None

    with pytest.raises(AnsibleConnectionFailure):
        connection._connect()


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_connect_fetch_device_error(mock_zpecloud_api, connection):
    """Fetching device by serial number fails."""
    connection._api_session = mock_zpecloud_api
    connection.host_serial_number = None
    connection.host_zpecloud_id = None

    remote_addr = "123456789"
    connection._play_context = Mock(remote_addr=remote_addr)

    mock_zpecloud_api.fetch_device_by_serial_number.return_value = (None, "some error")

    with pytest.raises(AnsibleConnectionFailure):
        connection._connect()

    assert mock_zpecloud_api.fetch_device_by_serial_number.call_count == 1
    mock_zpecloud_api.fetch_device_by_serial_number.assert_called_with(remote_addr)


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_connect_fetch_return_empty_content(mock_zpecloud_api, connection):
    """Fetching operation returned empty content."""
    connection._api_session = mock_zpecloud_api
    connection.host_serial_number = None
    connection.host_zpecloud_id = None

    remote_addr = "123456789"
    connection._play_context = Mock(remote_addr=remote_addr)

    mock_zpecloud_api.fetch_device_by_serial_number.return_value = ({}, None)

    with pytest.raises(AnsibleConnectionFailure):
        connection._connect()

    assert mock_zpecloud_api.fetch_device_by_serial_number.call_count == 1
    mock_zpecloud_api.fetch_device_by_serial_number.assert_called_with(remote_addr)


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_connect_success(mock_zpecloud_api, connection):
    """Connect working as expected."""
    connection._api_session = mock_zpecloud_api
    connection.host_serial_number = None
    connection.host_zpecloud_id = None

    remote_addr = "123456789"
    connection._play_context = Mock(remote_addr=remote_addr)

    host_id = "4321"
    mock_zpecloud_api.fetch_device_by_serial_number.return_value = (
        {"id": host_id},
        None,
    )

    mock_zpecloud_api.can_apply_profile_on_device.return_value = (True, None)

    connection._connect()

    assert mock_zpecloud_api.fetch_device_by_serial_number.call_count == 1
    mock_zpecloud_api.fetch_device_by_serial_number.assert_called_with(remote_addr)
    assert connection.host_serial_number == remote_addr
    assert connection.host_zpecloud_id == host_id


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_connect_device_not_ready(mock_zpecloud_api, connection):
    """Connect raise error because device is not ready to receive profiles.
    Device is considered ready if enrolled, and with status online or failover."""
    connection._api_session = mock_zpecloud_api
    connection.host_serial_number = None
    connection.host_zpecloud_id = None

    remote_addr = "123456789"
    connection._play_context = Mock(remote_addr=remote_addr)

    host_id = "4321"
    mock_zpecloud_api.fetch_device_by_serial_number.return_value = (
        {"id": host_id},
        None,
    )

    mock_zpecloud_api.can_apply_profile_on_device.return_value = (False, "some error")

    with pytest.raises(AnsibleConnectionFailure) as err:
        connection._connect()

    assert mock_zpecloud_api.fetch_device_by_serial_number.call_count == 1
    mock_zpecloud_api.fetch_device_by_serial_number.assert_called_with(remote_addr)
    assert connection.host_serial_number == remote_addr
    assert connection.host_zpecloud_id == host_id
    assert "Nodegrid device is not ready to receive profiles via ZPE Cloud." in str(err.value)


""" Tests for _connect """
""" Tests for exec_command """


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.exec_command")
def test_exec_command_as_default_user(mock_exec_command_super, connection):
    """Ansible runs profiles as Ansible user by default."""
    mock_exec_command_super.return_value = None

    ansible_cmd = "/bin/sh -c 'echo ~ && sleep 0'"
    expected_cmd = "su ansible -c 'echo ~ && sleep 0'"

    job_output = "/home/ansible"

    connection._play_context.executable = "/bin/sh"
    connection._wrapper_exec_command = Mock()
    connection._wrapper_exec_command.return_value = "wrapped command"
    connection._create_profile = Mock()
    connection._create_profile.return_value = "123"
    connection._apply_profile = Mock()
    connection._apply_profile.return_value = "456"
    connection._wait_job_to_finish = Mock()
    connection._wait_job_to_finish.return_value = (job_output, None)
    connection._delete_profile = Mock()

    result = connection.exec_command(cmd=ansible_cmd)

    assert result[0] == 0
    assert result[1] == job_output.encode("utf-8")
    assert connection._wrapper_exec_command.call_count == 1
    assert connection._wrapper_exec_command.call_args.args[0] == expected_cmd


""" Tests for exec_command """
""" Tests for put_file """


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.put_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.os")
def test_put_file_file_not_exist(mock_os, mock_super_put_file, connection):
    """Try to send a file to host that does not exist."""
    mock_os.path.exists.return_value = False

    mock_super_put_file.return_value = None

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleFileNotFound):
        connection.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.put_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.os")
def test_put_file_size_too_big(mock_os, mock_super_put_file, connection):
    """Try to send a file to host that is too big."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=connection.max_file_size_put_file + 1)

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        connection.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.read_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.put_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.os")
def test_put_file_fail_read_file(mock_os, mock_super_put_file, mock_read_file, connection):
    """Try to send a file to host but failed to read file."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=connection.max_file_size_put_file)
    mock_read_file.return_value = (None, "some error")

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        connection.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.read_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.put_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.os")
def test_put_file_fail_wait_job_finish(mock_os, mock_super_put_file, mock_read_file, connection):
    """Try to send a file to host but failed to wait for job."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=connection.max_file_size_put_file)
    mock_read_file.return_value = ("somefilecontent", None)

    connection._process_put_file = Mock()
    connection._wrapper_put_file = Mock()
    connection._create_profile = Mock()
    connection._apply_profile = Mock()
    connection._wait_job_to_finish = Mock()
    connection._wait_job_to_finish.return_value = (None, "some error")

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    with pytest.raises(AnsibleError):
        connection.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1
    assert connection._process_put_file.call_count == 1
    assert connection._wrapper_put_file.call_count == 1
    assert connection._create_profile.call_count == 1
    assert connection._apply_profile.call_count == 1
    assert connection._wait_job_to_finish.call_count == 1


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.read_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ConnectionBase.put_file")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.os")
def test_put_file_success(mock_os, mock_super_put_file, mock_read_file, connection):
    """Succeed to send file to host."""
    mock_super_put_file.return_value = None
    mock_os.path.exists.return_value = True
    mock_os.stat.return_value = Mock(st_size=connection.max_file_size_put_file)
    mock_read_file.return_value = ("somefilecontent", None)

    connection._process_put_file = Mock()
    connection._wrapper_put_file = Mock()
    connection._create_profile = Mock()
    connection._apply_profile = Mock()
    connection._wait_job_to_finish = Mock()
    connection._wait_job_to_finish.return_value = ("someoutput", None)
    connection._delete_profile = Mock()

    in_path = "/tmp/somepath"
    out_path = "/tmp/anotherpath"

    connection.put_file(in_path, out_path)

    mock_os.path.exists.assert_called_with(in_path.encode("utf-8"))
    mock_os.stat.assert_called_with(in_path.encode("utf-8"))
    assert mock_read_file.call_count == 1
    assert connection._process_put_file.call_count == 1
    assert connection._wrapper_put_file.call_count == 1
    assert connection._create_profile.call_count == 1
    assert connection._apply_profile.call_count == 1
    assert connection._wait_job_to_finish.call_count == 1
    assert connection._delete_profile.call_count == 1


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
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def close_connection(mock_zpecloud_api, connection, session, expected):
    """Test connection is being closed."""
    connection._api_session = MagicMock()
    mock_zpecloud_api.return_value.logout = MagicMock()
    mock_zpecloud_api.return_value.logout.return_value = ("", None)

    connection.close()

    if expected:
        mock_zpecloud_api.return_value.logout.assert_called_once()


""" Tests for close """
""" Tests for reset """


def test_reset_connection(connection):
    """Test if reset calls close and connect again."""
    connection.close = MagicMock()
    connection.close.return_value = None
    connection._connect = MagicMock()
    connection._connect.return_value = None

    connection.reset()

    connection.close.assert_called_once()
    connection._connect.assert_called_once()


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
def test_create_api_session_missing_required_configuration_raise_error(configuration, connection):
    """Playbook without credentials on variables, neither on env, must raise error."""
    _options = configuration

    def _get_option_side_effect(*args):
        return _options.get(*args)

    connection.get_option.side_effect = _get_option_side_effect

    with pytest.raises(AnsibleConnectionFailure):
        connection._create_api_session()


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_read_credentials_from_playbook_vars(mock_zpe_cloud_api, connection):
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
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(_options.get("username"), _options.get("password"))
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(_options.get("organization"))


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_read_credentials_from_env_variable(mock_zpe_cloud_api, connection):
    """Test reading configuration from environment variables."""
    mock_zpe_cloud_api.return_value.authenticate_with_password.return_value = ("", None)
    mock_zpe_cloud_api.return_value.change_organization.return_value = (True, None)
    connection.get_option.return_value = None

    _options = {
        "ZPECLOUD_USERNAME": "myuser@myemail.com",
        "ZPECLOUD_PASSWORD": "mysecurepassword",
        "ZPECLOUD_ORGANIZATION": "My organization",
    }

    os.environ["ZPECLOUD_USERNAME"] = _options.get("ZPECLOUD_USERNAME")
    os.environ["ZPECLOUD_PASSWORD"] = _options.get("ZPECLOUD_PASSWORD")
    os.environ["ZPECLOUD_ORGANIZATION"] = _options.get("ZPECLOUD_ORGANIZATION")

    connection._create_api_session()

    mock_zpe_cloud_api.assert_called_with("https://zpecloud.com")
    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(_options.get("ZPECLOUD_USERNAME"), _options.get("ZPECLOUD_PASSWORD"))
    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(_options.get("ZPECLOUD_ORGANIZATION"))


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_create_api_session_zpe_cloud_api_authentication_fail(mock_zpe_cloud_api, connection):
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

    mock_zpe_cloud_api.return_value.authenticate_with_password.assert_called_with(_options.get("username"), _options.get("password"))


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

    mock_zpe_cloud_api.return_value.change_organization.assert_called_with(_options.get("organization"))


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


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_request_fail(mock_zpecloud_api, connection):
    """Test wait job to finish but API request failed."""
    connection._api_session = mock_zpecloud_api
    mock_zpecloud_api.get_job.return_value = (None, "Some error")

    with pytest.raises(AnsibleError):
        connection._wait_job_to_finish("1234")


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_missing_status(mock_zpecloud_api, connection):
    """API response is invalid."""
    connection._api_session = mock_zpecloud_api
    mock_zpecloud_api.get_job.return_value = ("{}", None)

    with pytest.raises(AnsibleError):
        connection._wait_job_to_finish("1234")


@pytest.mark.parametrize(
    ("job_status"),
    [("Cancelled"), ("Timeout")],
)
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_failure(mock_zpecloud_api, connection, job_status):
    """Test wait job to finish but job finished with some failure status."""
    connection._api_session = mock_zpecloud_api

    response = json.dumps({"operation": {"status": job_status}})
    mock_zpecloud_api.get_job.return_value = (response, None)

    content, err = connection._wait_job_to_finish("1234")

    assert content is None
    assert job_status in err


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.time")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.requests")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_failed(mock_zpecloud_api, mock_requests, mock_time, connection):
    """
    Test wait job to finish with job failed status.
    In case of failure status with stdout available, the plugin will send stdout back to Ansible to decide if execution failed.
    """
    connection._api_session = mock_zpecloud_api

    failed_status = json.dumps({"operation": {"status": "Failed"}, "output_file": "someurl"})

    mock_zpecloud_api.get_job.return_value = (failed_status, None)

    mock_time.time.return_value = 0
    mock_time.sleep.return_value = None

    job_output = "somethinginbase64"
    mock_requests.get.return_value = Mock(content=job_output)

    content, err = connection._wait_job_to_finish("12314")

    assert err is None
    assert content == job_output

    assert mock_zpecloud_api.get_job.call_count == 1
    assert mock_requests.get.call_count == 1


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.time")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.requests")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_success(mock_zpecloud_api, mock_requests, mock_time, connection):
    """Test wait job to finish with sequence of job status."""
    connection._api_session = mock_zpecloud_api

    sending_status = json.dumps({"operation": {"status": "Sending"}, "output_file": ""})
    scheduled_status = json.dumps({"operation": {"status": "Scheduled"}, "output_file": ""})
    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})
    successful_status = json.dumps({"operation": {"status": "Successful"}, "output_file": "someurl"})

    mock_zpecloud_api.get_job = Mock()
    mock_zpecloud_api.get_job.side_effect = (
        [(sending_status, None)] * 2 + [(scheduled_status, None)] * 2 + [(started_status, None)] * 2 + [(successful_status, None)]
    )

    job_output = "somethinginbase64"
    mock_requests.get.return_value = Mock(content=job_output)

    mock_time.time.return_value = 0
    mock_time.sleep.return_value = None

    content, err = connection._wait_job_to_finish("12314")

    assert err is None
    assert content == job_output

    assert mock_zpecloud_api.get_job.call_count == 7
    assert mock_requests.get.call_count == 1
    assert mock_time.time.call_count == 8
    assert mock_time.sleep.call_count == 6


@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.time")
@patch("ansible_collections.zpe.zpecloud.plugins.connection.zpecloud.ZPECloudAPI")
def test_wait_job_to_finish_job_ansible_timeout(mock_zpecloud_api, mock_time, connection):
    """Ansible will timeout after some time polling job status."""
    connection._api_session = mock_zpecloud_api

    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})

    mock_zpecloud_api.get_job.return_value = (started_status, None)

    start_time = 1000  # seconds
    mock_time.time.side_effect = [
        start_time,  # start time
        start_time + 10,  # first iteration
        start_time + 1000,  # second iteration
        start_time + connection.timeout_wait_job_finish,  # third iteration (equal to timeout)
        start_time + connection.timeout_wait_job_finish + 1,  # timeout
    ]
    mock_time.sleep.return_value = None

    content, err = connection._wait_job_to_finish("12314")

    assert content is None
    assert err == "Job timeout"

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
