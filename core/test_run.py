#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from log.logger import Log
import pytest


class TestRun:
    dut = None
    executor = None
    LOGGER: Log = None
    plugins = {}

    @classmethod
    def fail(cls, message):
        cls.LOGGER.error(message)
        pytest.fail(message)

    @classmethod
    def block(cls, message):
        cls.LOGGER.blocked(message)
        pytest.fail(message)

    @classmethod
    def exception(cls, message):
        cls.LOGGER.exception(message)
        pytest.fail(message)
