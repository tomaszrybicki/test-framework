#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import random

import pytest

from test_tools import fs_utils
from test_tools.dd import Dd
from test_tools.disk_utils import Filesystem
from test_tools.fio.fio import Fio
from test_tools.fio.fio_param import ReadWrite
from test_utils.filesystem.file import File
from test_utils.os_utils import sync, Udev
from .io_class_common import *


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_lba(prepare_and_cleanup):
    """Write data to random lba and check if it is cached according to range
    defined in ioclass rule"""
    cache, core = prepare()
    ioclass_id = 1
    min_cached_lba = 56
    max_cached_lba = 200
    iterations = 100
    dd_size = Size(1, Unit.Blocks512)
    dd_count = 1

    # Prepare ioclass config
    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"lba:ge:{min_cached_lba}&lba:le:{max_cached_lba}&done",
        ioclass_config_path=ioclass_config_path,
    )

    # Prepare cache for test
    casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

    cache.flush_cache()

    # Check if lbas from defined range are cached
    dirty_count = 0
    # '8' step is set to prevent writing cache line more than once
    TestProperties.LOGGER.info(f"Writing to one sector in each cache line from range.")
    for lba in range(min_cached_lba, max_cached_lba, 8):
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{core.system_path}")
            .count(dd_count)
            .block_size(dd_size)
            .seek(lba)
        )
        dd.run()
        sync()
        dirty_count += 1

        stats = cache.get_cache_statistics(io_class_id=ioclass_id)
        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == dirty_count
        ), f"LBA {lba} not cached"

    cache.flush_cache()

    # Check if lba outside of defined range are not cached
    TestProperties.LOGGER.info(f"Writing to random sectors outside of cached range.")
    for i in range(iterations):
        rand_lba = random.randrange(2000)
        if min_cached_lba <= rand_lba <= max_cached_lba:
            continue
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{core.system_path}")
            .count(dd_count)
            .block_size(dd_size)
            .seek(rand_lba)
        )
        dd.run()
        sync()

        stats = cache.get_cache_statistics(io_class_id=ioclass_id)
        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == 0
        ), f"Inappropriately cached lba: {rand_lba}"


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_request_size(prepare_and_cleanup):
    cache, core = prepare()

    ioclass_id = 1
    iterations = 100

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"request_size:ge:8192&request_size:le:16384&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

    Udev.disable()

    # Check if requests with appropriate size are cached
    TestProperties.LOGGER.info(
        f"Check if requests with size within defined range are cached"
    )
    cached_req_sizes = [Size(2, Unit.Blocks4096), Size(4, Unit.Blocks4096)]
    for i in range(iterations):
        cache.flush_cache()
        req_size = random.choice(cached_req_sizes)
        dd = (
            Dd()
            .input("/dev/zero")
            .output(core.system_path)
            .count(1)
            .block_size(req_size)
            .oflag("direct")
        )
        dd.run()
        stats = cache.get_cache_statistics(io_class_id=ioclass_id)
        assert (
            stats["dirty"].get_value(Unit.Blocks4096)
            == req_size.value / Unit.Blocks4096.value
        )

    cache.flush_cache()

    # Check if requests with inappropriate size are not cached
    TestProperties.LOGGER.info(
        f"Check if requests with size outside defined range are not cached"
    )
    not_cached_req_sizes = [
        Size(1, Unit.Blocks4096),
        Size(8, Unit.Blocks4096),
        Size(16, Unit.Blocks4096),
    ]
    for i in range(iterations):
        req_size = random.choice(not_cached_req_sizes)
        dd = (
            Dd()
            .input("/dev/zero")
            .output(core.system_path)
            .count(1)
            .block_size(req_size)
            .oflag("direct")
        )
        dd.run()
        stats = cache.get_cache_statistics(io_class_id=ioclass_id)
        assert stats["dirty"].get_value(Unit.Blocks4096) == 0


@pytest.mark.parametrize("filesystem", list(Filesystem) + [False])
@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_direct(prepare_and_cleanup, filesystem):
    cache, core = prepare()
    cache.flush_cache()
    Udev.disable()

    ioclass_id = 1
    io_size = Size(random.randint(1000, 2000), Unit.Blocks4096)

    # direct IO class
    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule="direct",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

    fio = (
        Fio().create_command()
             .size(io_size)
             .offset(io_size)
             .read_write(ReadWrite.write)
             .target(f"{mountpoint}/tmp_file" if filesystem else core.system_path)
    )

    if filesystem:
        TestProperties.LOGGER.info(
            f"Preparing {filesystem.name} filesystem and mounting {core.system_path} at"
            f" {mountpoint}"
        )
        core.create_filesystem(filesystem)
        core.mount(mountpoint)
        sync()
    else:
        TestProperties.LOGGER.info("Testing on raw exported object")

    base_occupancy = cache.get_cache_statistics(per_io_class=True,
                                                io_class_id=ioclass_id)["occupancy"]

    TestProperties.LOGGER.info(f"Buffered writes to {'file' if filesystem else 'device'}")
    fio.run()
    sync()
    new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                               io_class_id=ioclass_id)["occupancy"]
    assert new_occupancy == base_occupancy, \
        "Buffered writes were cached!\n" \
        f"Expected: {base_occupancy}, actual: {new_occupancy}"

    TestProperties.LOGGER.info(f"Direct writes to {'file' if filesystem else 'device'}")
    fio.direct()
    fio.run()
    sync()
    new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                               io_class_id=ioclass_id)["occupancy"]
    assert new_occupancy == base_occupancy + io_size, \
        "Wrong number of direct writes was cached!\n" \
        f"Expected: {base_occupancy + io_size}, actual: {new_occupancy}"

    TestProperties.LOGGER.info(f"Buffered reads from {'file' if filesystem else 'device'}")
    fio.remove_param("readwrite").remove_param("direct")
    fio.read_write(ReadWrite.read)
    fio.run()
    sync()
    new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                               io_class_id=ioclass_id)["occupancy"]
    assert new_occupancy == base_occupancy, \
        "Buffered reads did not cause reclassification!" \
        f"Expected occupancy: {base_occupancy}, actual: {new_occupancy}"

    TestProperties.LOGGER.info(f"Direct reads from {'file' if filesystem else 'device'}")
    fio.direct()
    fio.run()
    sync()
    new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                               io_class_id=ioclass_id)["occupancy"]
    assert new_occupancy == base_occupancy + io_size, \
        "Wrong number of direct reads was cached!\n" \
        f"Expected: {base_occupancy + io_size}, actual: {new_occupancy}"


@pytest.mark.parametrize("filesystem", Filesystem)
@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_metadata(prepare_and_cleanup, filesystem):
    cache, core = prepare()
    cache.flush_cache()
    Udev.disable()

    ioclass_id = random.randint(1, ioclass_config.MAX_IO_CLASS_ID)
    # metadata IO class
    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule="metadata&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

    TestProperties.LOGGER.info(f"Preparing {filesystem.name} filesystem "
                               f"and mounting {core.system_path} at {mountpoint}")
    core.create_filesystem(filesystem)
    core.mount(mountpoint)
    sync()

    requests_to_metadata_before = cache.get_cache_statistics(
        per_io_class=True, io_class_id=ioclass_id)["write total"]
    TestProperties.LOGGER.info("Creating 20 test files")
    files = []
    for i in range(1, 21):
        file_path = f"{mountpoint}/test_file_{i}"
        dd = (
            Dd()
            .input("/dev/urandom")
            .output(file_path)
            .count(random.randint(5, 50))
            .block_size(Size(1, Unit.MebiByte))
            .oflag("sync")
        )
        dd.run()
        files.append(File(file_path))

    TestProperties.LOGGER.info("Checking requests to metadata")
    requests_to_metadata_after = cache.get_cache_statistics(
        per_io_class=True, io_class_id=ioclass_id)["write total"]
    if requests_to_metadata_after == requests_to_metadata_before:
        pytest.xfail("No requests to metadata while creating files!")

    requests_to_metadata_before = requests_to_metadata_after
    TestProperties.LOGGER.info("Renaming all test files")
    for file in files:
        file.move(f"{file.full_path}_renamed")
        sync()

    TestProperties.LOGGER.info("Checking requests to metadata")
    requests_to_metadata_after = cache.get_cache_statistics(
        per_io_class=True, io_class_id=ioclass_id)["write total"]
    if requests_to_metadata_after == requests_to_metadata_before:
        pytest.xfail("No requests to metadata while renaming files!")

    requests_to_metadata_before = requests_to_metadata_after
    test_dir_path = f"{mountpoint}/test_dir"
    TestProperties.LOGGER.info(f"Creating directory {test_dir_path}")
    fs_utils.create_directory(path=test_dir_path)

    TestProperties.LOGGER.info(f"Moving test files into {test_dir_path}")
    for file in files:
        file.move(test_dir_path)
        sync()

    TestProperties.LOGGER.info("Checking requests to metadata")
    requests_to_metadata_after = cache.get_cache_statistics(
        per_io_class=True, io_class_id=ioclass_id)["write total"]
    if requests_to_metadata_after == requests_to_metadata_before:
        pytest.xfail("No requests to metadata while moving files!")

    TestProperties.LOGGER.info(f"Removing {test_dir_path}")
    fs_utils.remove(path=test_dir_path, force=True, recursive=True)

    TestProperties.LOGGER.info("Checking requests to metadata")
    requests_to_metadata_after = cache.get_cache_statistics(
        per_io_class=True, io_class_id=ioclass_id)["write total"]
    if requests_to_metadata_after == requests_to_metadata_before:
        pytest.xfail("No requests to metadata while deleting directory with files!")
