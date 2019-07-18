#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging
import pytest
from api.cas import casadm
from test_package.conftest import base_prepare
from test_package.test_properties import TestProperties
from storage_devices.disk import DiskType

LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 0, "cache_count": 1, "cache_type": "optane"}, ],
                         indirect=True)
def test_cli_start_stop_default_value(prepare_and_cleanup, shortcut):
    prepare()
    cache_device = next(
        disk for disk in TestProperties.dut.disks if disk.disk_type == DiskType.optane)
    casadm.start_cache(cache_device, shortcut=shortcut, force=True)

    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 1
    assert parsed_output["caches"]["1"]["path"] == cache_device.system_path

    casadm.stop_cache(cache_id=1, shortcut=shortcut)

    output = casadm.list_caches(shortcut=shortcut)
    assert len(casadm.parse_list_caches()["caches"]) == 0
    assert output.stdout == "No caches running"


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 1, "cache_count": 1, "cache_type": "optane"}],
                         indirect=True)
def test_cli_add_remove_default_value(prepare_and_cleanup, shortcut):
    prepare()
    cache_device = next(
        disk for disk in TestProperties.dut.disks if disk.disk_type == DiskType.optane)
    casadm.start_cache(cache_device, shortcut=shortcut, force=True)

    core_device = next(
        disk for disk in TestProperties.dut.disks if disk.disk_type != DiskType.optane)
    casadm.add_core(1, core_device, shortcut=shortcut)

    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["cores"]) == 1
    assert parsed_output["cores"]["/dev/cas1-1"]["path"] == core_device.system_path

    casadm.remove_core(1, 1, shortcut=shortcut)
    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 1
    assert len(parsed_output["cores"]) == 0

    casadm.stop_cache(cache_id=1, shortcut=shortcut)

    output = casadm.list_caches(shortcut=shortcut)
    parsed_output = casadm.parse_list_caches()
    assert len(parsed_output["caches"]) == 0
    assert len(parsed_output["cores"]) == 0
    assert output.stdout == "No caches running"


def prepare():
    base_prepare()
