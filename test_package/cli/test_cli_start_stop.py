#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging
import pytest
from api import casadm


LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("shortcut", [True, False])
def test_cli_start_stop_default_value(prepare_and_cleanup, shortcut):
    casadm.start("/dev/nvme0n1p1", shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert "/dev/nvme0n1p1" in output.stdout  # TODO:create casadm -L parsing api

    casadm.stop(cache_id=1, shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert output.stdout == "No caches running"


@pytest.mark.parametrize("shortcut", [True, False])
def test_cli_add_remove_default_value(prepare_and_cleanup, shortcut):
    casadm.start("/dev/nvme0n1p1", shortcut=shortcut)

    casadm.add_core(1, "/dev/sdb1", shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert "/dev/sdb1" in output.stdout  # TODO:create casadm -L parsing api

    output = casadm.remove_core(1, 1, shortcut=shortcut)
    assert "/dev/sdb1" not in output.stdout  # TODO:create casadm -L parsing api

    casadm.stop(cache_id=1, shortcut=shortcut)

    output = casadm.list(shortcut=shortcut)
    assert output.stdout == "No caches running"
