#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from test_package.test_properties import TestProperties


def help(shortcut: bool = False):
    return TestProperties.executor.execute(help_cmd(shortcut))
