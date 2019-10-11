#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from datetime import timedelta

from config import configuration


class BaseExecutor:
    def execute(self, command, timeout: timedelta = timedelta(hours=1)):
        raise NotImplementedError()

    def execute_in_background(self, command, timeout: timedelta = timedelta(hours=1)):
        command += "&> /dev/null &echo $!"
        output = self.execute(command, timeout)

        if output is not None:
            return output.stdout

    def execute_with_proxy(self, command, timeout: timedelta = timedelta(hours=1)):
        if configuration.proxy_command:
            command = f"{configuration.proxy_command} && {command}"

        return self.execute(command, timeout)

    def wait_cmd_finish(self, pid: int):
        self.execute(f"while [ -e /proc/{pid} ]; do sleep 0.1; done")

    def run_expect_success(self, command):
        output = self.execute(command)
        if output.exit_code != 0:
            raise Exception(f"Exception occurred while trying to execute '{command}' command.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output

    def run_expect_fail(self, command):
        output = self.execute(command)
        if output.exit_code == 0:
            raise Exception(f"Command '{command}' executed properly but error was expected.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output
