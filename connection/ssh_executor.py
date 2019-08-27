#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from datetime import timedelta

import paramiko

from connection.base_executor import BaseExecutor
from test_utils.output import Output


class SshExecutor(BaseExecutor):
    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.ssh = paramiko.SSHClient()
        self.connect(username, password, port)

    def __del__(self):
        self.ssh.close()

    def connect(self, user, passwd, port, timeout: timedelta = timedelta(seconds=30)):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.ip, username=user, password=passwd,
                             port=port, timeout=timeout.total_seconds())
        except paramiko.SSHException:
            raise ConnectionError(f"An exception occurred while trying to connect to {self.ip}")

    def disconnect(self):
        try:
            self.ssh.close()
        except Exception:
            raise Exception(f"An exception occurred while trying to disconnect from {self.ip}")

    def execute(self, command, timeout: timedelta = timedelta(hours=1)):
        try:
            (stdin, stdout, stderr) = self.ssh.exec_command(command,
                                                            timeout=timeout.total_seconds())
        except paramiko.SSHException as e:
            raise ConnectionError(f"An exception occurred while executing command '{command}' on"
                                  f" {self.ip}\n{e}")

        return Output(stdout.read(), stderr.read(), stdout.channel.recv_exit_status())
