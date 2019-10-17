#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from datetime import timedelta
from core.test_run import TestRun

class BaseExecutor:
    def _execute(self, command, timeout):
        raise NotImplementedError()

    def run(self, command, timeout: timedelta = timedelta(hours=1)):
        if TestRun.dut and TestRun.dut.env:
            command = f"{TestRun.dut.env} && {command}"

        return self._execute(command, timeout)

    def run_in_background(self, command, timeout: timedelta = timedelta(hours=1)):
        command += "&> /dev/null &echo $!"
        output = self.run(command, timeout)

        if output is not None:
            return output.stdout

    def wait_cmd_finish(self, pid: int):
        self.run(f"tail --pid={pid} -f /dev/null")

    def run_expect_success(self, command):
        output = self.run(command)
        if output.exit_code != 0:
            raise Exception(f"Exception occurred while trying to execute '{command}' command.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output

    def run_expect_fail(self, command):
        output = self.run(command)
        if output.exit_code == 0:
            raise Exception(f"Command '{command}' executed properly but error was expected.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output
