#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from config import configuration
from connection.base_executor import BaseExecutor
from test_package.test_properties import TestProperties


class DummyExecutor(BaseExecutor):
    def execute(self, command, timeout=None):
        print(command)

    def execute_with_proxy(self, command, timeout=None):
        if configuration.proxy_command:
            command = f"{configuration.proxy_command} && {command}"
        else:
            TestProperties.LOGGER.info("No proxy command specified for 'execute_with_proxy'")
        print(command)
