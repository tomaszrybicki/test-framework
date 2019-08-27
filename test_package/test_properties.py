#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging


class TestProperties:
    dut = None
    executor = None
    LOGGER = logging.getLogger("Test logger")

    @staticmethod
    def execute_command_and_check_if_passed(command):
        output = TestProperties.executor.execute(command)
        if output.exit_code != 0:
            raise Exception(f"Exception occured while trying to execute '{command}' command.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output

    @staticmethod
    def execute_command_and_check_if_failed(command):
        output = TestProperties.executor.execute(command)
        if output.exit_code == 0:
            raise Exception(f"Command '{command}' executed properly but error was expected.\n"
                            f"stdout: {output.stdout}\nstderr: {output.stderr}")
        return output
