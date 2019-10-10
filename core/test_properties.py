#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging

from connection.base_executor import BaseExecutor


class TestProperties:
    dut = None
    executor: BaseExecutor = None
    LOGGER = logging.getLogger("Test logger")
