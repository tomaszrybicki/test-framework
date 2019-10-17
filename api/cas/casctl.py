#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from core.test_run import TestRun


def help(shortcut: bool = False):
    return TestRun.executor.execute(ctl_help(shortcut))


def start():
    return TestRun.executor.execute(ctl_start())


def stop(flush: bool = False):
    return TestRun.executor.execute(ctl_stop(flush))


def init(force: bool = False):
    return TestRun.executor.execute(ctl_init(force))
