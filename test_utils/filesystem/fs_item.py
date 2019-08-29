#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import ntpath
from test_tools import fs_utils


class FsItem:
    def __init__(self, full_path):
        self.full_path = full_path
        self.parent_dir = self.get_parent_dir(self.full_path)
        self.name = self.get_name(self.full_path)
        self.modification_time = None
        self.owner = None
        self.group = None
        self.permissions = FsPermissions()
        self.size = None

    @staticmethod
    def get_name(path):
        head, tail = ntpath.split(path)
        return tail or ntpath.basename(head)

    @staticmethod
    def get_parent_dir(path):
        head, tail = ntpath.split(path)
        if tail:
            return head
        else:
            head, tail = ntpath.split(head)
            return head

    def __str__(self):
        return self.full_path

    def chmod_numerical(self, permissions: int, recursive: bool = False):
        fs_utils.chmod_numerical(self.full_path, permissions, recursive)
        self.refresh_item()

    def chmod(self,
              permissions: fs_utils.Permissions,
              users: fs_utils.PermissionsUsers,
              sign: fs_utils.PermissionSign = fs_utils.PermissionSign.set,
              recursive: bool = False):
        fs_utils.chmod(self.full_path, permissions, users, sign=sign, recursive=recursive)
        output = fs_utils.ls(f"{self.full_path}")
        self.refresh_item()

    def chown(self, owner, group, recursive: bool = False):
        fs_utils.chown(self.full_path, owner, group, recursive)
        self.refresh_item()

    def refresh_item(self):
        updated_file = fs_utils.parse_ls_output(fs_utils.ls(self.full_path))[0]
        self.size = updated_file.size
        self.permissions = updated_file.permissions
        self.modification_time = updated_file.modification_time
        self.owner = updated_file.owner
        self.group = updated_file.group


class FsPermissions:
    def __init__(self, user=None, group=None, other=None):
        self.user = user
        self.group = group
        self.other = other

    def __eq__(self, other):
        return self.user == other.user and self.group == other.group and self.other == other.other
