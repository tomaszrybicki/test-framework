#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


class BaseExecutor:
    def execute(self, command, timeout=None):
        raise NotImplementedError()

    def execute_with_proxy(self, command, timeout=None):
        raise NotImplementedError()
