#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
from test_utils.filesystem.file import File


class Symlink(File):
    def __init__(self, full_path, target):
        File.__init__(self, full_path)
        self.target = target
