#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


from enum import IntEnum
from test_utils.size import Size, Unit
from test_tools import disk_utils
from test_tools.disk_utils import PartitionTable
from storage_devices.partition import Partition
from storage_devices.device import Device
from core.test_run import TestRun
import re
import time
import json


class DiskType(IntEnum):
    hdd = 0
    hdd4k = 1
    sata = 2
    nand = 3
    optane = 4


class DiskTypeSetBase:
    def resolved(self):
        raise NotImplementedError()

    def types(self):
        raise NotImplementedError()

    def json(self):
        return json.dumps({
            "type": "set",
            "values": [t.name for t in self.types()]
        })

    def __lt__(self, other):
        return min(self.types()) < min(other.types())

    def __le__(self, other):
        return min(self.types()) <= min(other.types())

    def __eq__(self, other):
        return min(self.types()) == min(other.types())

    def __ne__(self, other):
        return min(self.types()) != min(other.types())

    def __gt__(self, other):
        return min(self.types()) > min(other.types())

    def __ge__(self, other):
        return min(self.types()) >= min(other.types())


class DiskTypeSet(DiskTypeSetBase):
    def __init__(self, *args):
        self.__types = set(*args)

    def resolved(self):
        return True

    def types(self):
        return self.__types


class DiskTypeLowerThan(DiskTypeSetBase):
    def __init__(self, disk_name):
        self.__disk_name = disk_name

    def resolved(self):
        return self.__disk_name in TestRun.disks

    def types(self):
        if not self.resolved():
            raise LookupError("Disk type not resolved!")
        disk_type = TestRun.disks[self.__disk_name].disk_type
        return set(filter(lambda d: d < disk_type, [*DiskType]))

    def json(self):
        return json.dumps({
            "type": "operator",
            "name": "lt",
            "args": [self.__disk_name]
        })


class Disk(Device):
    def __init__(
        self,
        path,
        disk_type: DiskType,
        serial_number,
        block_size,
    ):
        Device.__init__(self, path)
        self.serial_number = serial_number
        self.block_size = Unit(block_size)
        self.disk_type = disk_type
        self.partitions = []

    def create_partitions(
            self,
            sizes: [],
            partition_table_type=disk_utils.PartitionTable.gpt
    ):
        if disk_utils.create_partition_table(self, partition_table_type):
            self.partition_table = partition_table_type
            partition_type = disk_utils.PartitionType.primary

            partition_number_offset = 0
            for s in sizes:
                size = Size(
                    s.get_value(self.block_size) - self.block_size.value, self.block_size)
                if partition_table_type == disk_utils.PartitionTable.msdos and \
                        len(sizes) > 4 and len(self.partitions) == 3:
                    disk_utils.create_partition(self,
                                                Size.zero(),
                                                4,
                                                disk_utils.PartitionType.extended,
                                                Unit.MebiByte,
                                                True)
                    partition_type = disk_utils.PartitionType.logical
                    partition_number_offset = 1

                partition_number = len(self.partitions) + 1 + partition_number_offset
                if disk_utils.create_partition(self,
                                               size,
                                               partition_number,
                                               partition_type,
                                               Unit.MebiByte,
                                               True):
                    new_part = Partition(self,
                                         partition_type,
                                         partition_number)
                    self.partitions.append(new_part)

    def umount_all_partitions(self):
        TestRun.LOGGER.info(
            f"Umounting all partitions from: {self.system_path}")
        cmd = f'umount -l {self.system_path}*?'
        output = TestRun.executor.run(cmd)

    def remove_partitions(self):
        for part in self.partitions:
            if part.is_mounted():
                part.unmount()
        if disk_utils.remove_partitions(self):
            self.partitions.clear()

    def __str__(self):
        disk_str = f'system path: {self.system_path}, type: {self.disk_type}, ' \
            f'serial: {self.serial_number}, size: {self.size}, ' \
            f'block size: {self.block_size}, partitions:\n'
        for part in self.partitions:
            disk_str += f'\t{part}'
        return disk_str
