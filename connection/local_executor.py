#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import subprocess
from datetime import timedelta

from config import configuration
from connection.base_executor import BaseExecutor
from test_package.test_properties import TestProperties
from test_utils.output import Output


class LocalExecutor(BaseExecutor):
    def execute(self, command, timeout: timedelta = timedelta(hours=1)):
        completed_process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds())

        output = Output(
            completed_process.stdout.decode("utf-8"),
            completed_process.stderr.decode("utf-8"),
            completed_process.returncode)
        return output

    def execute_with_proxy(self, command, timeout: timedelta = timedelta(hours=1)):
        if configuration.proxy_command:
            command = f"{configuration.proxy_command} && {command}"
        else:
            TestProperties.LOGGER.info("No proxy command specified for 'execute_with_proxy'")

        completed_process = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout.total_seconds())

        output = Output(
            completed_process.stdout,
            completed_process.stderr,
            completed_process.returncode)
        return output
