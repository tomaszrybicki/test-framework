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


TestRun.setup = __setup
