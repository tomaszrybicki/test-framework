#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from test_tools.dd import Dd
from test_utils.filesystem.fs_item import FsItem
from test_utils.size import Size
from test_tools import fs_utils
from core.test_run import TestRun
from test_tools import fs_utils
from test_utils.filesystem.fs_item import FsItem


class File(FsItem):
    def __init__(self, full_path):
        FsItem.__init__(self, full_path)

    def compare(self, other_file):
        return fs_utils.compare(str(self), str(other_file))

    def diff(self, other_file):
        return fs_utils.diff(str(self), str(other_file))

    def md5sum(self, binary=True):
        output = TestRun.executor.run(
            f"md5sum {'-b' if binary else ''} {self.full_path}")
        if output.exit_code != 0:
            raise Exception(f"Md5sum command execution failed! {output.stdout}\n{output.stderr}")
        return output.stdout.split()[0]

    def read(self):
        return fs_utils.read_file(str(self))

    def write(self, content, overwrite: bool = True):
        fs_utils.write_file(str(self), content, overwrite)
        self.refresh_item()

    @staticmethod
    def create_file(path: str):
        fs_utils.create_file(path)
        output = fs_utils.ls_item(f"{path}")
        return fs_utils.parse_ls_output(output)[0]

    def padding(self, size: Size):
        dd = Dd().input("/dev/zero").output(self).count(1).block_size(size)
        dd.run()
        self.refresh_item()

    def remove(self, force: bool = False, ignore_errors: bool = False):
        fs_utils.remove(str(self), force=force, ignore_errors=ignore_errors)

    def copy(self,
             destination,
             force: bool = False,
             recursive: bool = False,
             dereference: bool = False):
        fs_utils.copy(str(self), destination, force, recursive, dereference)
        if fs_utils.check_if_directory_exists(destination):
            path = f"{destination}{'/' if destination[-1] != '/' else ''}{self.name}"
        else:
            path = destination
        output = fs_utils.ls_item(f"{path}")
        return fs_utils.parse_ls_output(output)[0]
