#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from enum import IntEnum, Enum
from utils.size import Size, Unit


class CacheLineSize(IntEnum):
    LINE_4KiB = Size(4, Unit.KibiByte)
    LINE_8KiB = Size(8, Unit.KibiByte)
    LINE_16KiB = Size(16, Unit.KibiByte)
    LINE_32KiB = Size(32, Unit.KibiByte)
    LINE_64KiB = Size(64, Unit.KibiByte)
    DEFAULT = LINE_4KiB


class CacheMode(Enum):
    WT = "wt"
    WB = "wb"
    WA = "wa"
    PT = "pt"
    WO = "wo"
    DEFAULT = WT


# TODO: Use case for this will be to iterate over configurations (kernel params such as
# TODO: such as io scheduler, metadata layout) and prepare env before starting cache
class CacheConfig:
    def __init__(self):
        pass
