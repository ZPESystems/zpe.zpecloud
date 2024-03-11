# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import pytest
import sys
from unittest.mock import MagicMock, Mock
from unittest.mock import patch

from ansible.playbook.play_context import PlayContext

from ansible.errors import AnsibleError, AnsibleActionFail

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
    action._api_session = MagicMock()
    action._play_context = Mock()
    action._api_session = Mock()
    action._create_api_session = Mock()

    return action


""" Tests for _validate_version """


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("4.2.0", True),
        ("5.10.10", True),
        ("6.100.1000", True),
        ("4.2.0.0", False),
        ("v4.2.0", False),
        ("v6.0.3 (Feb 22 2024 - 22:10:02)", False),
    ],
)
def test_software_upgrade_validate_version(version, expected, action):
    """Verify if version validation is right."""
    res = action._validate_version(version)

    assert res == expected


""" Tests for _validate_version """
""" Tests for _extract_version """


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("v5.100.1000 (Feb 22 2050 - 22:10:02)", "5.100.1000"),
        ("v6.0.3 (Feb 22 2024 - 22:10:02)", "6.0.3"),
        ("v6.0.s (Feb 22 2024 - 22:10:02)", None),
        ("v4.0 (Feb 22 2024 - 22:10:02)", None),
    ],
)
def test_software_upgrade_extract_version(version, expected, action):
    """Verify if version extraction is right."""
    res = action._extract_version(version)

    print("res: ", res)
    print("expected: ", expected)
    assert res == expected


""" Tests for _extract_version """
""" Tests for _is_upgrade """


@pytest.mark.parametrize(
    ("current", "next"),
    [
        ("", ""),
        ("", "5.0.0"),
        ("5.0.0", ""),
        ("5.0.0.0", ""),
        ("", "5.0.0.0"),
    ],
)
def test_software_upgrade_is_upgrade_for_wrong_format(current, next, action):
    """Verify if version extraction is right."""
    res, err = action._is_upgrade(current, next)

    assert res is None
    assert err is not None


@pytest.mark.parametrize(
    ("current", "next", "expected"),
    [
        ("5.0.0", "6.0.0", True),
        ("5.0.0", "5.1.0", True),
        ("5.0.0", "5.0.1", True),
        ("5.10.10", "6.0.3", True),
        ("5.1.1", "4.1.1", False),
        ("5.1.1", "5.0.1", False),
        ("5.1.1", "5.1.0", False),
    ],
)
def test_software_upgrade_is_upgrade(current, next, expected, action):
    """Verify if version extraction is right."""
    res, err = action._is_upgrade(current, next)

    assert res == expected, f"Upgrade from {current} to {next} - Is upgrade? {res}"
    assert err is None


""" Tests for _is_upgrade """
""" Tests for _get_version_id_from_list """


""" Tests for _get_version_id_from_list """
""" Tests for _apply_software_upgrade """

""" Tests for _apply_software_upgrade """
""" Tests for _get_software_upgrade_job_id """

""" Tests for _get_software_upgrade_job_id """
""" Tests for _wait_job_to_finish """


def test_software_upgrade_wait_job_to_finish_request_fail(action):
    """Test wait job to finish but API request failed."""
    action._api_session.get_job.return_value = (None, "Some error")

    with pytest.raises(AnsibleActionFail):
        action._wait_job_to_finish("1234")


def test_software_upgrade_wait_job_to_finish_missing_status(action):
    """API response is invalid."""
    action._api_session.get_job.return_value = ("{}", None)

    with pytest.raises(AnsibleError):
        action._wait_job_to_finish("1234")


@pytest.mark.parametrize(
    ("job_status"),
    [("Cancelled"), ("Timeout"), ("Failed")],
)
def test_software_upgrade_wait_job_to_finish_job_fail(action, job_status):
    """Test wait job to finish but job finished with some failure status."""
    response = json.dumps({"operation": {"status": job_status}})
    action._api_session.get_job.return_value = (response, None)

    content, err = action._wait_job_to_finish("1234")

    assert content is None
    assert job_status in err


@patch("ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.time")
def test_software_upgrade_wait_job_to_finish_job_success(mock_time, action):
    """Test wait job to finish with sequence of job status."""
    sending_status = json.dumps({"operation": {"status": "Sending"}, "output_file": ""})
    scheduled_status = json.dumps(
        {"operation": {"status": "Scheduled"}, "output_file": ""}
    )
    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})
    successful_status = json.dumps(
        {"operation": {"status": "Successful"}, "output_file": "someurl"}
    )

    action._api_session.get_job = Mock()
    action._api_session.get_job.side_effect = (
        [(sending_status, None)] * 2
        + [(scheduled_status, None)] * 2
        + [(started_status, None)] * 2
        + [(successful_status, None)]
    )

    mock_time.time.return_value = 0
    mock_time.sleep.return_value = None

    content, err = action._wait_job_to_finish("12314")

    assert err is None
    assert action._api_session.get_job.call_count == 7
    assert mock_time.time.call_count == 8
    assert mock_time.sleep.call_count == 6


@patch("ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.time")
def test_software_upgrade_wait_job_to_finish_job_ansible_timeout(mock_time, action):
    """Ansible will timeout after some time polling job status."""
    started_status = json.dumps({"operation": {"status": "Started"}, "output_file": ""})

    action._api_session.get_job.return_value = (started_status, None)

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
    assert err == "Job timeout"

    assert action._api_session.get_job.call_count == 3
    assert mock_time.time.call_count == 5
    assert mock_time.sleep.call_count == 3


""" Tests for _wait_job_to_finish """
""" Tests for run """


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_empty_args(zpecloud_action_base_run, action):
    """Task does not have parameters."""
    zpecloud_action_base_run.return_value = {}

    action._task.args.get.return_value = None

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert str(err.value) == "NG OS version was not provided."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_wrong_version_format(zpecloud_action_base_run, action):
    """User type wrong version format."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect
    action._play_context.remote_addr.return_value = "1234"

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert str(err.value) == "NG OS does not match the expected format."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_remote_addr_not_found(zpecloud_action_base_run, action):
    """Host does not have remote address."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect
    action._play_context.remote_addr = None

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert str(err.value) == "Remote serial number from host was not found."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_failed_fetch_device(zpecloud_action_base_run, action):
    """Failed to search device by serial number."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()
    action._api_session.fetch_device_by_serial_number.return_value = (
        None,
        "some error",
    )

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert "Failed to fetch device in ZPE Cloud." in str(err.value)


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_failed_get_device_id(zpecloud_action_base_run, action):
    """Failed to get device ID while search by serial number."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    action._api_session.fetch_device_by_serial_number.return_value = ({}, None)

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert str(err.value) == "Failed to get device ID."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_failed_get_device_version(zpecloud_action_base_run, action):
    """Failed to get device version while search by serial number."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id},
        None,
    )

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert str(err.value) == "Failed to get current device version."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_same_version_return_ok(zpecloud_action_base_run, action):
    """Device already running desired version, then finish with OK."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "6.0.0"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    result = action.run()

    assert action.host_serial_number == remote_addr
    assert result["ok"] is True
    assert f"Device already on Nodegrid version {device_version}" in result["msg"]


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_get_wrong_version(zpecloud_action_base_run, action):
    """Got wrong format of version."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "6.1"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert str(err.value) == "Nodegrid version does not match the expected format."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_downgrade_not_allowed(zpecloud_action_base_run, action):
    """User requested a downgrade, but did not set flag to true."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "6.1.0"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    result = action.run()

    assert action.host_serial_number == remote_addr
    assert result["failed"] is True
    assert "Software downgrade is not allowed." in result["msg"]


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_fail_get_release(zpecloud_action_base_run, action):
    """Failed to get Nodegrid versions."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.10.0"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    action._api_session.get_available_os_version.return_value = (
        None,
        "some error",
    )

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert str(err.value) == "Failed to get Nodegrid OS versions from ZPE Cloud."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_not_release_match(zpecloud_action_base_run, action):
    """Desired version as not found on zpe cloud."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "6.0.0", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.100.0"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    action._api_session.get_available_os_version.return_value = ([], None)

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert str(err.value) == "Failed to get Nodegrid OS version ID."


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_wait_job_failed(zpecloud_action_base_run, action):
    """Software upgrade job failed."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "5.10.10", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v5.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = (None, "some error")

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert "Failed to apply software upgrade." in str(err.value)


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_failed_get_detail(zpecloud_action_base_run, action):
    """Failed to get detail of job."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "5.10.10", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v5.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("Success", None)

    action._api_session.get_device_detail.return_value = (None, "some error")

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert "Failed to get device detail." in str(err.value)


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_failed_get_device_version_detail(zpecloud_action_base_run, action):
    """Device version not found on detail content."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "5.10.10", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v5.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("Success", None)

    action._api_session.get_device_detail.return_value = ("{}", None)

    with pytest.raises(AnsibleActionFail) as err:
        action.run()

    assert action.host_serial_number == remote_addr
    assert "ailed to get current device version." in str(err.value)


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_ugprade_fail(zpecloud_action_base_run, action):
    """Software upgrade failed and device keeps with same version."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "5.10.10", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v5.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("Success", None)

    action._api_session.get_device_detail.return_value = ('{"version": "5.9.10"}', None)

    result = action.run()

    assert action.host_serial_number == remote_addr
    assert result["failed"] is True
    assert "Failed to upgrade device to Nodegrid version" in result["msg"]


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_ugprade_succeed(zpecloud_action_base_run, action):
    """Software upgrade succeed."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "5.10.10", "allow_downgrade": False}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v5.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("Success", None)

    action._api_session.get_device_detail.return_value = (
        '{"version": "5.10.10"}',
        None,
    )

    result = action.run()

    assert action.host_serial_number == remote_addr
    assert result["changed"] is True


@patch(
    "ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.ZPECloudActionBase.run"
)
def test_software_upgrade_run_downgrade_succeed(zpecloud_action_base_run, action):
    """Software downgrade succeed."""
    zpecloud_action_base_run.return_value = {}

    _options = {"version": "4.10.10", "allow_downgrade": True}

    def _get_option_side_effect(*args):
        return _options.get(*args)

    action._task.args.get.side_effect = _get_option_side_effect

    remote_addr = "1234"
    action._play_context.remote_addr = remote_addr

    action._create_api_session = Mock()

    device_id = "567"
    device_version = "5.9.10"
    action._api_session.fetch_device_by_serial_number.return_value = (
        {"id": device_id, "version": device_version},
        None,
    )

    os_name = "v4.10.10 (Jan 15 2024 - 07:45:20)"
    os_id = "12"
    action._api_session.get_available_os_version.return_value = (
        [{"id": os_id, "name": os_name}],
        None,
    )

    job_id = "999"
    action._apply_software_upgrade = Mock()
    action._apply_software_upgrade.return_value = job_id

    action._wait_job_to_finish = Mock()
    action._wait_job_to_finish.return_value = ("Success", None)

    action._api_session.get_device_detail.return_value = (
        '{"version": "4.10.10"}',
        None,
    )

    result = action.run()

    assert action.host_serial_number == remote_addr
    assert result["changed"] is True


""" Tests for run """
