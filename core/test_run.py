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
    def step(cls, message):
        return cls.LOGGER.step(message)

    @classmethod
    def group(cls, message):
        return cls.LOGGER.group(message)

    @classmethod
    def iteration(cls, iterable):
        items = list(iterable)
        for i, item in enumerate(items, start=1):
            cls.LOGGER.start_iteration(f"Iteration {i}/{len(items)}")
            yield item
            TestRun.LOGGER.end_iteration()

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
