#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from enum import IntEnum


# TODO: change to some sort of Size class when it is implemented
class CacheLineSize(IntEnum):
    LINE_4KiB = 4096
    LINE_8KiB = 8192
    LINE_16KiB = 16384
    LINE_32KiB = 32768
    LINE_64KiB = 65536
    DEFAULT = LINE_4KiB


# TODO: Use case for this will be to iterate over configurations (kernel params such as
# TODO: such as io schedler, metadata layout) and prepare env before starting cache
class CacheConfig:
    def __init__(self):
        pass
