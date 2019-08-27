#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import subprocess
from datetime import timedelta

from connection.base_executor import BaseExecutor
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
            completed_process.stdout,
            completed_process.stderr,
            completed_process.returncode)
        return output
