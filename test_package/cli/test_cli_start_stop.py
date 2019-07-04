#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging
import pytest
from api.cas import casadm
from test_package.conftest import base_prepare


LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 1, "cache_count": 1}],
                         indirect=True)
def test_cli_start_stop_default_value(prepare_and_cleanup, shortcut):
    prepare(prepare_and_cleanup)

    casadm.start("/dev/nvme0n1p1", shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert "/dev/nvme0n1p1" in output.stdout  # TODO:create casadm -L parsing api

    casadm.stop(cache_id=1, shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert output.stdout == "No caches running"


@pytest.mark.parametrize("shortcut", [True, False])
@pytest.mark.parametrize('prepare_and_cleanup',
                         [{"core_count": 1, "cache_count": 1}],
                         indirect=True)
def test_cli_add_remove_default_value(prepare_and_cleanup, shortcut):
    prepare(prepare_and_cleanup)

    casadm.start("/dev/nvme0n1p1", shortcut=shortcut)

    casadm.add_core(1, "/dev/sdb2", shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert "/dev/sdb2" in output.stdout  # TODO:create casadm -L parsing api

    output = casadm.remove_core(1, 1, shortcut=shortcut)
    assert "/dev/sdb2" not in output.stdout  # TODO:create casadm -L parsing api

    casadm.stop(cache_id=1, shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert output.stdout == "No caches running"


def prepare(prepare_fixture):
    base_prepare(prepare_fixture)
