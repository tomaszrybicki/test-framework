#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import pytest
from IPy import IP

from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from test_utils import disk_finder
from test_utils.dut import Dut
import core.test_run


TestRun = core.test_run.TestRun


@classmethod
def __configure(cls, config):
    config.addinivalue_line(
        "markers",
        "require_disk(name, type): require disk of specific type, otherwise skip"
    )


TestRun.configure = __configure


@classmethod
def __prepare(cls, item):
    cls.item = item
    req_disks = list(map(lambda mark: mark.args, cls.item.iter_markers(name="require_disk")))
    cls.req_disks = dict(req_disks)
    if len(req_disks) != len(cls.req_disks):
        raise ValueError("Disk name specified more than once!")


TestRun.prepare = __prepare


@classmethod
def __setup_disks(cls):
    cls.disks = {}
    req_items = list(cls.req_disks.items())
    req_items.sort(
        key=lambda disk: (lambda disk_name, disk_type: max(disk_type))(*disk)
    )
    for disk_name, disk_type in req_items:
        cls.disks[disk_name] = next(filter(
            lambda disk: disk.disk_type in disk_type and disk not in cls.disks.values(),
            cls.dut.disks
        ))
        if not cls.disks[disk_name]:
            raise pytest.skip("Unable to find requested disk!")


TestRun.__setup_disks = __setup_disks


@classmethod
def __setup(cls, dut_config):
    if 'ip' in dut_config:
        try:
            IP(dut_config['ip'])
        except ValueError:
            raise Exception("IP address from configuration file is in invalid format.")
        if 'user' in dut_config and 'password' in dut_config:
            cls.executor = SshExecutor(
                dut_config['ip'],
                dut_config['user'],
                dut_config['password']
            )
        else:
            raise Exception("There is no credentials in config file.")
    else:
        cls.executor = LocalExecutor()

    if 'disks' not in dut_config:
        dut_config["disks"] = disk_finder.find_disks()

    cls.dut = Dut(dut_config)

    cls.__setup_disks()


TestRun.setup = __setup
