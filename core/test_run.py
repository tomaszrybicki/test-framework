#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging


class TestRun:
    dut = None
    executor = None
    LOGGER = logging.getLogger("Test logger")
    plugins = {}
