#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
import pytest
from test_package.test_properties import TestProperties
from test_package.conftest import base_prepare as base_prepare

LOGGER = logging.getLogger(__name__)


def setup_module():
    LOGGER.warning("Entering setup method")


@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"cache_type": "optane", "cache_count": 1}],
                         indirect=True)
def test_example(prepare_and_cleanup):
    prepare(prepare_and_cleanup)
    LOGGER.info("Test run")
    output = TestProperties.executor.execute("hostname -I | awk '{print $1}'")
    LOGGER.info(output.stdout)
    assert output.stdout.strip() == TestProperties.dut.ip


def prepare(prepare_fixture):
    base_prepare(prepare_fixture)
    LOGGER.info("Test prepare")
