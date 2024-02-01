# Copyright (c) 2024, ZPE Systems <zpesystems.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import pytest

from ansible.inventory.data import InventoryData

from ansible_collections.zpe.zpecloud.plugins.inventory.zpecloud_nodegrid_inventory import InventoryModule


@pytest.fixture(scope="module")
def inventory():
    r = InventoryModule()
    r.inventory = InventoryData()
    return r


def test_verify_wrong_config(inventory):
    assert inventory.verify_file("zpecloud_foobar.yml") is False


def test_verify_wrong_filename(tmp_path, inventory):
    file = tmp_path / "zpecloud-123.yml"
    file.touch()
    assert inventory.verify_file(str(file)) is False


@pytest.mark.parametrize("filename", ["zpecloud.yml", "zpecloud.yaml"])
def test_verify_correct_file(tmp_path, inventory, filename):
    file = tmp_path / filename
    file.touch()
    assert inventory.verify_file(str(file)) is True


def test_parse_empty_config(inventory):
    pass
