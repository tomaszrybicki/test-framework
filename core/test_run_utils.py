#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from IPy import IP

from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from test_utils import disk_finder
from test_utils.dut import Dut
import core.test_run


TestRun = core.test_run.TestRun


@classmethod
def __prepare(cls, dut_config):
    if hasattr(dut_config, 'ip'):
        try:
            IP(dut_config.ip)
            if hasattr(dut_config, 'user') and hasattr(dut_config, 'password'):
                executor = SshExecutor(dut_config.ip, dut_config.user, dut_config.password)
                cls.executor = executor
            else:
                raise Exception("There is no credentials in config file.")
            if hasattr(dut_config, 'disks'):
                cls.dut = Dut({'ip': dut_config.ip, 'disks': dut_config.disks})
            else:
                cls.dut = Dut(
                    {'ip': dut_config.ip, 'disks': disk_finder.find_disks()})
        except ValueError:
            raise Exception("IP address from configuration file is in invalid format.")
    elif hasattr(dut_config, 'disks'):
        cls.executor = LocalExecutor()
        cls.dut = Dut({'disks': dut_config.disks})
    else:
        cls.executor = LocalExecutor()
        cls.dut = Dut({'disks': disk_finder.find_disks()})


TestRun.prepare = __prepare
