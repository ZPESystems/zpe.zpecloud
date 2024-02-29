# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import pytest
import sys
from unittest.mock import MagicMock, Mock
from unittest.mock import patch

from ansible.playbook.play_context import PlayContext

from ansible.errors import AnsibleError, AnsibleFileNotFound, AnsibleActionFail

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
def test_validate_version(version, expected, action):
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
def test_extract_version(version, expected, action):
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
def test_is_upgrade_for_wrong_format(current, next, action):
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
        ("5.1.1", "4.1.1", False),
        ("5.1.1", "5.0.1", False),
        ("5.1.1", "5.1.0", False),
    ],
)
def test_is_upgrade(current, next, expected, action):
    """Verify if version extraction is right."""
    res, err = action._is_upgrade(current, next)

    assert res == expected
    assert err is None


""" Tests for _is_upgrade """
""" Tests for _get_version_id_from_list """


""" Tests for _get_version_id_from_list """
""" Tests for _apply_software_upgrade """

""" Tests for _apply_software_upgrade """
""" Tests for _get_software_upgrade_job_id """

""" Tests for _get_software_upgrade_job_id """
""" Tests for _wait_job_to_finish """


def test_wait_job_to_finish_request_fail(action):
    """Test wait job to finish but API request failed."""
    action._api_session.get_job.return_value = (None, "Some error")

    with pytest.raises(AnsibleActionFail):
        action._wait_job_to_finish("1234")


def test_wait_job_to_finish_missing_status(action):
    """API response is invalid."""
    action._api_session.get_job.return_value = ("{}", None)

    with pytest.raises(AnsibleError):
        action._wait_job_to_finish("1234")


@pytest.mark.parametrize(
    ("job_status"),
    [("Cancelled"), ("Timeout"), ("Failed")],
)
def test_wait_job_to_finish_job_fail(action, job_status):
    """Test wait job to finish but job finished with some failure status."""
    response = json.dumps({"operation": {"status": job_status}})
    action._api_session.get_job.return_value = (response, None)

    content, err = action._wait_job_to_finish("1234")

    assert content is None
    assert job_status in err


@patch("ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.time")
@patch("ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.requests")
def test_wait_job_to_finish_job_success(mock_requests, mock_time, action):
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

    job_output = "somethinginbase64"
    mock_requests.get.return_value = Mock(content=job_output)

    mock_time.time.return_value = 0
    mock_time.sleep.return_value = None

    content, err = action._wait_job_to_finish("12314")

    assert err is None
    assert content == job_output

    assert action._api_session.get_job.call_count == 7
    assert mock_requests.get.call_count == 1
    assert mock_time.time.call_count == 8
    assert mock_time.sleep.call_count == 6


@patch("ansible_collections.zpe.zpecloud.plugins.action.software_upgrade.time")
def test_wait_job_to_finish_job_ansible_timeout(mock_time, action):
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
    assert err == "Timeout"

    assert action._api_session.get_job.call_count == 3
    assert mock_time.time.call_count == 5
    assert mock_time.sleep.call_count == 3


""" Tests for _wait_job_to_finish """
""" Tests for run """


""" Tests for run """
