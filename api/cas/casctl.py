#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from test_package.test_properties import TestProperties


def help(shortcut: bool = False):
    return TestProperties.executor.execute(ctl_help(shortcut))


def start():
    return TestProperties.executor.execute(ctl_start())


def stop(flush: bool = False):
    return TestProperties.executor.execute(ctl_stop(flush))


def init(force: bool = False):
    return TestProperties.executor.execute(ctl_init(force))
