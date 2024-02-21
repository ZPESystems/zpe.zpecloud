# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import os
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch


from ansible_collections.zpe.zpecloud.plugins.plugin_utils.utils import (
    exponential_backoff_delay,
)


""" Tests for exponential_backoff_delay """


@pytest.mark.parametrize(
    ("attempt", "max_delay", "expected"),
    [
        (0, 256, 1),
        (1, 256, 1),
        (2, 256, 2),
        (3, 256, 4),
        (7, 256, 64),
        (10, 256, 256),
    ],
)
def test_exponential_backoff_delay(attempt, max_delay, expected):
    """Check output exponential backoff delay."""
    assert exponential_backoff_delay(attempt, max_delay) == expected


""" Tests for exponential_backoff_delay """