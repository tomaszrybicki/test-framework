#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import pytest
import random
import time
from api.cas import casadm
from api.cas import ioclass_config
from api.cas import casadm_parser
from test_tools.dd import Dd
from cas_configuration.cache_config import CacheMode, CleaningPolicy
from test_package.conftest import base_prepare
from test_package.test_properties import TestProperties
from storage_devices.disk import DiskType
from storage_devices.device import Device
from test_tools.disk_utils import Filesystem, create_filesystem, mount, unmount
from test_utils.size import Size, Unit
from test_utils.os_utils import sync, Udev

ioclass_config_path = "/tmp/opencas_ioclass.conf"
mountpoint = "/tmp/cas1-1"
exported_obj_path = "/dev/cas1-1"
cache_id = 1


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_file_extension(prepare_and_cleanup):
    prepare()
    iterations = 50
    ioclass_id = 1
    tested_extension = "tmp"
    wrong_extensions = ["tm", "tmpx", "txt", "t", "", "123"]
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 10

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"extension:{tested_extension}&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    TestProperties.LOGGER.info(
        f"Preparing filesystem and mounting {exported_obj_path} at {mountpoint}"
    )
    exported_obj = Device(exported_obj_path)
    create_filesystem(exported_obj, Filesystem.ext3)
    mount(exported_obj, mountpoint)

    flush_cache(cache_id)

    # Check if file with proper extension is cached
    dd = (
        Dd()
        .input("/dev/zero")
        .output(f"{mountpoint}/test_file.{tested_extension}")
        .count(dd_count)
        .block_size(dd_size)
    )
    TestProperties.LOGGER.info(f"Writing to file with cached extension.")
    for i in range(iterations):
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert stats["dirty"].get_value(Unit.Blocks4096) == (i + 1) * dd_count

    flush_cache(cache_id)

    # Check if file with improper extension is not cached
    TestProperties.LOGGER.info(f"Writing to file with no cached extension.")
    for ext in wrong_extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert stats["dirty"].get_value(Unit.Blocks4096) == 0


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_file_extension_preexisting_filesystem(prepare_and_cleanup):
    """Create files on filesystem, add device with filesystem as a core,
        write data to files and check if they are cached properly"""
    core_device = prepare()
    ioclass_id = 1
    extensions = ["tmp", "tm", "out", "txt", "log", "123"]
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 10

    TestProperties.LOGGER.info(f"Preparing files on raw block device")
    casadm.remove_core(cache_id=cache_id, core_id=1)
    create_filesystem(core_device, Filesystem.ext3)
    mount(core_device, mountpoint)

    # Prepare files
    for ext in extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
    unmount(core_device)

    # Prepare ioclass config
    rule = "|".join([f"extension:{ext}" for ext in extensions])
    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"{rule}&done",
        ioclass_config_path=ioclass_config_path,
    )

    # Prepare cache for test
    TestProperties.LOGGER.info(f"Adding device with preexisting data as a core")
    casadm.add_core(cache_id=cache_id, core_dev=core_device)
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    exported_obj = Device(exported_obj_path)
    mount(exported_obj, mountpoint)

    flush_cache(cache_id)

    # Check if files with proper extensions are cached
    TestProperties.LOGGER.info(f"Writing to file with cached extension.")
    for ext in extensions:
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/test_file.{ext}")
            .count(dd_count)
            .block_size(dd_size)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert (
            stats["dirty"].get_value(Unit.Blocks4096)
            == (extensions.index(ext) + 1) * dd_count
        )


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_lba(prepare_and_cleanup):
    """Write data to random lba and check if it is cached according to range
    defined in ioclass rule"""
    core_device = prepare()
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
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    flush_cache(cache_id=cache_id)

    # Check if lbas from defined range are cached
    dirty_count = 0
    # '8' step is set to prevent writting cache line more than once
    TestProperties.LOGGER.info(f"Writing to one sector in each cache line from range.")
    for lba in range(min_cached_lba, max_cached_lba, 8):
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{exported_obj_path}")
            .count(dd_count)
            .block_size(dd_size)
            .seek(lba)
        )
        dd.run()
        sync()
        dirty_count += 1

        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == dirty_count
        ), f"LBA {lba} not cached"

    flush_cache(cache_id)

    # Check if lba outside of defined range are not cached
    TestProperties.LOGGER.info(f"Writing to random sectors outside of cached range.")
    for i in range(iterations):
        rand_lba = random.randrange(2000)
        if min_cached_lba <= rand_lba <= max_cached_lba:
            continue
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{exported_obj_path}")
            .count(dd_count)
            .block_size(dd_size)
            .seek(rand_lba)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )

        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == 0
        ), f"Inappropriately cached lba: {rand_lba}"


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_process_name(prepare_and_cleanup):
    """Check if data generated by process with particular name is cached"""
    prepare()

    ioclass_id = 1
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 1
    iterations = 100

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"process_name:dd&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    flush_cache(cache_id)

    Udev.disable()

    TestProperties.LOGGER.info(f"Check if all data generated by dd process is cached.")
    for i in range(iterations):
        dd = (
            Dd()
            .input("/dev/zero")
            .output(exported_obj_path)
            .count(dd_count)
            .block_size(dd_size)
            .seek(i)
        )
        dd.run()
        sync()
        time.sleep(0.1)
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert stats["dirty"].get_value(Unit.Blocks4096) == (i + 1) * dd_count


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_request_size(prepare_and_cleanup):
    prepare()

    ioclass_id = 1
    iterations = 100

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"request_size:ge:8192&request_size:le:16384&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    Udev.disable()

    # Check if requests with appropriate size are cached
    TestProperties.LOGGER.info(
        f"Check if requests with size within defined range are cached"
    )
    cached_req_sizes = [Size(2, Unit.Blocks4096), Size(4, Unit.Blocks4096)]
    for i in range(iterations):
        flush_cache(cache_id)
        req_size = random.choice(cached_req_sizes)
        dd = (
            Dd()
            .input("/dev/zero")
            .output(exported_obj_path)
            .count(1)
            .block_size(req_size)
            .oflag("direct")
        )
        dd.run()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert (
            stats["dirty"].get_value(Unit.Blocks4096)
            == req_size.value / Unit.Blocks4096.value
        )

    flush_cache(cache_id)

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
            .output(exported_obj_path)
            .count(1)
            .block_size(req_size)
            .oflag("direct")
        )
        dd.run()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert stats["dirty"].get_value(Unit.Blocks4096) == 0


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_pid(prepare_and_cleanup):
    prepare()

    ioclass_id = 1
    iterations = 20
    dd_count = 100
    dd_size = Size(4, Unit.KibiByte)

    Udev.disable()

    # Since 'dd' has to be executed right after writing pid to 'ns_last_pid',
    # 'dd' command is created and is appended to 'echo' command instead of running it
    dd_command = str(
        Dd()
        .input("/dev/zero")
        .output(exported_obj_path)
        .count(dd_count)
        .block_size(dd_size)
    )

    for i in range(iterations):
        flush_cache(cache_id)

        output = TestProperties.executor.execute("cat /proc/sys/kernel/ns_last_pid")
        if output.exit_code != 0:
            raise Exception(
                f"Failed to retrieve pid. stdout: {output.stdout} \n stderr :{output.stderr}"
            )

        # Few pids might be used by system during test preparation
        pid = int(output.stdout) + 50

        ioclass_config.add_ioclass(
            ioclass_id=ioclass_id,
            eviction_priority=1,
            allocation=True,
            rule=f"pid:eq:{pid}&done",
            ioclass_config_path=ioclass_config_path,
        )
        casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

        TestProperties.LOGGER.info(f"Running dd with pid {pid}")
        # pid saved in 'ns_last_pid' has to be smaller by one than target dd pid
        dd_and_pid_command = (
            f"echo {pid-1} > /proc/sys/kernel/ns_last_pid && {dd_command}"
        )
        output = TestProperties.executor.execute(dd_and_pid_command)
        if output.exit_code != 0:
            raise Exception(
                f"Failed to run dd with target pid. "
                f"stdout: {output.stdout} \n stderr :{output.stderr}"
            )
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert stats["dirty"].get_value(Unit.Blocks4096) == dd_count

        ioclass_config.remove_ioclass(ioclass_id)


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_file_offset(prepare_and_cleanup):
    prepare()

    ioclass_id = 1
    iterations = 100
    dd_size = Size(4, Unit.KibiByte)
    dd_count = 1
    min_cached_offset = 16384
    max_cached_offset = 65536

    ioclass_config.add_ioclass(
        ioclass_id=ioclass_id,
        eviction_priority=1,
        allocation=True,
        rule=f"file_offset:gt:{min_cached_offset}&file_offset:lt:{max_cached_offset}&done",
        ioclass_config_path=ioclass_config_path,
    )
    casadm.load_io_classes(cache_id=cache_id, file=ioclass_config_path)

    TestProperties.LOGGER.info(
        f"Preparing filesystem and mounting {exported_obj_path} at {mountpoint}"
    )
    exported_obj = Device(exported_obj_path)
    create_filesystem(exported_obj, Filesystem.ext3)
    mount(exported_obj, mountpoint)

    flush_cache(cache_id)

    # Since ioclass rule consists of strict inequalities, 'seek' can't be set to first
    # nor last sector
    min_seek = int((min_cached_offset + Unit.Blocks4096.value) / Unit.Blocks4096.value)
    max_seek = int(
        (max_cached_offset - min_cached_offset - Unit.Blocks4096.value)
        / Unit.Blocks4096.value
    )
    TestProperties.LOGGER.info(f"Writing to file within cached offset range")
    for i in range(iterations):
        file_offset = random.choice(range(min_seek, max_seek))
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/tmp_file")
            .count(dd_count)
            .block_size(dd_size)
            .seek(file_offset)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == 1
        ), f"Offset not cached: {file_offset}"
        flush_cache(cache_id)

    min_seek = 0
    max_seek = int(min_cached_offset / Unit.Blocks4096.value)
    TestProperties.LOGGER.info(f"Writing to file outside of cached offset range")
    for i in range(iterations):
        file_offset = random.choice(range(min_seek, max_seek))
        dd = (
            Dd()
            .input("/dev/zero")
            .output(f"{mountpoint}/tmp_file")
            .count(dd_count)
            .block_size(dd_size)
            .seek(file_offset)
        )
        dd.run()
        sync()
        stats = casadm_parser.get_statistics(
            cache_id=cache_id, per_io_class=True, io_class_id=ioclass_id
        )
        assert (
            stats["dirty"].get_value(Unit.Blocks4096) == 0
        ), f"Inappropriately cached offset: {file_offset}"


def flush_cache(cache_id):
    casadm.flush(cache_id=cache_id)
    sync()
    stats = casadm_parser.get_statistics(cache_id=cache_id)
    assert stats["dirty"].get_value(Unit.Blocks4096) == 0


def prepare():
    base_prepare()
    ioclass_config.remove_ioclass_config()
    cache_device = next(
        disk
        for disk in TestProperties.dut.disks
        if disk.disk_type in [DiskType.optane, DiskType.nand]
    )
    core_device = next(
        disk
        for disk in TestProperties.dut.disks
        if (
            disk.disk_type.value > cache_device.disk_type.value and disk != cache_device
        )
    )

    cache_device.create_partitions([Size(500, Unit.MebiByte)])
    core_device.create_partitions([Size(1, Unit.GigaByte)])

    cache_device = cache_device.partitions[0]
    core_device = core_device.partitions[0]

    TestProperties.LOGGER.info(f"Staring cache")
    casadm.start_cache(cache_device, cache_mode=CacheMode.WB, force=True)
    TestProperties.LOGGER.info(f"Setting cleaning policy to NOP")
    casadm.set_param_cleaning(cache_id=cache_id, policy=CleaningPolicy.nop)
    TestProperties.LOGGER.info(f"Adding core device")
    casadm.add_core(cache_id=cache_id, core_dev=core_device)

    ioclass_config.create_ioclass_config(
        add_default_rule=False, ioclass_config_path=ioclass_config_path
    )
    # To make test more precise all workload except of tested ioclass should be
    # put in pass-through mode
    ioclass_config.add_ioclass(
        ioclass_id=0,
        eviction_priority=22,
        allocation=False,
        rule=f"unclassified",
        ioclass_config_path=ioclass_config_path,
    )

    output = TestProperties.executor.execute(f"mkdir -p {mountpoint}")
    if output.exit_code != 0:
        raise Exception(f"Failed to create mountpoint")

    return core_device
