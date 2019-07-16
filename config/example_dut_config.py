#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from test_utils.size import Size, Unit


ip = "x.x.x.x"
disks = [{'path': '/dev/device_name',
          'serial': 'ABC',  # disk serial number
          'type': 'nand',  # disk_type
          'size': Size(10, Unit.GibiByte),
          'blocksize': Size(1, Unit.Blocks512)}]
user = "example_user"
password = "example_password"
