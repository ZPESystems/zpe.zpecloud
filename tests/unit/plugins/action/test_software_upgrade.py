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

from ansible_collections.zpe.zpecloud.plugins.action.software_upgrade import ActionModule

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("ignore")

