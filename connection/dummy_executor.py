#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from connection.base_executor import BaseExecutor


class DummyExecutor(BaseExecutor):
    def _execute(self, command, timeout=None):
        print(command)

    def rsync(self, src, dst, delete=False, timeout=None):
        print(f'COPY FROM "{src}" TO "{dst}"')
