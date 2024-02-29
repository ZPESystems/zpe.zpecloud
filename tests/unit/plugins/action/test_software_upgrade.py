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
