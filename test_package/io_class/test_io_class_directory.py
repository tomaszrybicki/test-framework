#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from datetime import datetime

from test_utils.filesystem.directory import Directory
from test_utils.os_utils import drop_caches
from .test_io_classification import *


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_directory_depth(prepare_and_cleanup):
    cache, core = prepare()
    cache.flush_cache()
    Udev.disable()

    for filesystem in [Filesystem.xfs, Filesystem.ext3, Filesystem.ext4]:
        TestProperties.LOGGER.info(f"Preparing {filesystem.name} filesystem "
                                   f"and mounting {core.system_path} at {mountpoint}")
        core.create_filesystem(filesystem)
        core.mount(mountpoint)
        sync()

        base_dir_path = f"{mountpoint}/base_dir"
        TestProperties.LOGGER.info(f"Creating the base directory: {base_dir_path}")
        fs_utils.create_directory(base_dir_path)

        nested_dir_path = base_dir_path
        random_depth = random.randint(40, 80)
        for i in range(random_depth):
            nested_dir_path += f"/dir_{i}"
        TestProperties.LOGGER.info(f"Creating a nested directory: {nested_dir_path}")
        fs_utils.create_directory(path=nested_dir_path, parents=True)

        # Test classification in nested dir by reading a previously unclassified file
        TestProperties.LOGGER.info("Creating the first file in the nested directory")
        test_file_1 = File(f"{nested_dir_path}/test_file_1")
        dd = (
            Dd()
            .input("/dev/urandom")
            .output(test_file_1.full_path)
            .count(random.randint(1, 200))
            .block_size(Size(1, Unit.MebiByte))
        )
        dd.run()
        sync()
        drop_caches(3)
        test_file_1.refresh_item()

        ioclass_id = random.randint(1, ioclass_config.MAX_IO_CLASS_ID)
        # directory IO class
        ioclass_config.add_ioclass(
            ioclass_id=ioclass_id,
            eviction_priority=1,
            allocation=True,
            rule=f"directory:{base_dir_path}",
            ioclass_config_path=ioclass_config_path,
        )
        casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

        base_occupancy = cache.get_cache_statistics(per_io_class=True,
                                                    io_class_id=ioclass_id)["occupancy"]
        TestProperties.LOGGER.info("Reading the file in the nested directory")
        dd = (
            Dd()
            .input(test_file_1.full_path)
            .output("/dev/null")
            .block_size(Size(1, Unit.MebiByte))
        )
        dd.run()

        new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                                   io_class_id=ioclass_id)["occupancy"]
        assert new_occupancy == base_occupancy + test_file_1.size, \
            "Wrong occupancy after reading file!\n" \
            f"Expected: {base_occupancy + test_file_1.size}, actual: {new_occupancy}"

        # Test classification in nested dir by creating a file
        base_occupancy = new_occupancy
        TestProperties.LOGGER.info("Creating the second file in the nested directory")
        test_file_2 = File(f"{nested_dir_path}/test_file_2")
        dd = (
            Dd()
            .input("/dev/urandom")
            .output(test_file_2.full_path)
            .count(random.randint(1, 200))
            .block_size(Size(1, Unit.MebiByte))
        )
        dd.run()
        sync()
        drop_caches(3)
        test_file_2.refresh_item()

        new_occupancy = cache.get_cache_statistics(per_io_class=True,
                                                   io_class_id=ioclass_id)["occupancy"]
        assert new_occupancy == base_occupancy + test_file_2.size, \
            "Wrong occupancy after creating file!\n" \
            f"Expected: {base_occupancy + test_file_2.size}, actual: {new_occupancy}"

        core.unmount()

        ioclass_config.remove_ioclass_config(ioclass_config_path=ioclass_config_path)
        ioclass_config.create_ioclass_config(
            add_default_rule=False, ioclass_config_path=ioclass_config_path
        )
        ioclass_config.add_ioclass(
            ioclass_id=0,
            eviction_priority=22,
            allocation=False,
            rule="unclassified",
            ioclass_config_path=ioclass_config_path,
        )


@pytest.mark.parametrize(
    "prepare_and_cleanup", [{"core_count": 1, "cache_count": 1}], indirect=True
)
def test_ioclass_directory_operations(prepare_and_cleanup):
    def create_files_with_classification_delay_check(
            directory: Directory, ioclass_id: int):
        start_time = datetime.now()
        occupancy_after = cache.get_cache_statistics(
            per_io_class=True, io_class_id=ioclass_id)["occupancy"]
        dd_blocks = 10
        dd_size = Size(dd_blocks, Unit.Blocks4096)
        classified_files_no = file_counter = 0
        unclassified_files = []
        time_from_start = datetime.now() - start_time
        while time_from_start < ioclass_config.MAX_CLASSIFICATION_DELAY * 1.5:
            occupancy_before = occupancy_after
            file_path = f"{directory.full_path}/test_file_{file_counter}"
            file_counter += 1
            time_from_start = datetime.now() - start_time
            (Dd().input("/dev/zero").output(file_path).oflag("sync")
             .block_size(Size(1, Unit.Blocks4096)).count(dd_blocks).run())
            occupancy_after = cache.get_cache_statistics(
                per_io_class=True, io_class_id=ioclass_id)["occupancy"]
            if occupancy_after - occupancy_before < dd_size:
                unclassified_files.append(file_path)
                if time_from_start <= ioclass_config.MAX_CLASSIFICATION_DELAY:
                    continue
                pytest.xfail("Reclassification time too long!")
            classified_files_no += 1

        if len(unclassified_files):
            TestProperties.LOGGER.info("Rewriting unclassified test files...")
            for file_path in unclassified_files:
                (Dd().input("/dev/zero").output(file_path).oflag("sync")
                 .block_size(Size(1, Unit.Blocks4096)).count(dd_blocks).run())

    def read_files_with_reclassification_check(
            target_ioclass_id: int, source_ioclass_id: int, directory: Directory, with_delay: bool):
        start_time = datetime.now()
        target_occupancy_after = cache.get_cache_statistics(
            per_io_class=True, io_class_id=target_ioclass_id)["occupancy"]
        source_occupancy_after = cache.get_cache_statistics(
            per_io_class=True, io_class_id=source_ioclass_id)["occupancy"]
        unclassified_files = []

        for file in [item for item in directory.ls() if item is File]:
            target_occupancy_before = target_occupancy_after
            source_occupancy_before = source_occupancy_after
            time_from_start = datetime.now() - start_time
            (Dd().input(file.full_path).output("/dev/null")
             .block_size(Size(1, Unit.Blocks4096)).run())
            target_occupancy_after = cache.get_cache_statistics(
                per_io_class=True, io_class_id=target_ioclass_id)["occupancy"]
            source_occupancy_after = cache.get_cache_statistics(
                per_io_class=True, io_class_id=source_ioclass_id)["occupancy"]
            if target_occupancy_after > target_occupancy_before:
                pytest.xfail("Target IO class occupancy lowered!")
            elif target_occupancy_after - target_occupancy_before < file.size:
                unclassified_files.append(file)
                if with_delay and time_from_start <= ioclass_config.MAX_CLASSIFICATION_DELAY:
                    continue
                pytest.xfail("Target IO class occupancy not changed properly!")
            if source_occupancy_after >= source_occupancy_before:
                if file not in unclassified_files:
                    unclassified_files.append(file)
                if with_delay and time_from_start <= ioclass_config.MAX_CLASSIFICATION_DELAY:
                    continue
                pytest.xfail("Source IO class occupancy not changed properly!")

        if len(unclassified_files):
            TestProperties.LOGGER.info("Rereading unclassified test files...")
            sync()
            drop_caches(3)
            for file in unclassified_files:
                (Dd().input(file.full_path).output("/dev/null")
                 .block_size(Size(1, Unit.Blocks4096)).run())

    cache, core = prepare()
    cache.flush_cache()
    Udev.disable()

    for filesystem in [Filesystem.ext3, Filesystem.ext4, Filesystem.xfs]:
        proper_ids = list(range(1, ioclass_config.MAX_IO_CLASS_ID + 1))
        random.shuffle(proper_ids)
        ioclass_id_1 = proper_ids[0]
        classified_dir_path_1 = f"{mountpoint}/dir_{ioclass_id_1}"
        ioclass_id_2 = proper_ids[1]
        classified_dir_path_2 = f"{mountpoint}/dir_{ioclass_id_2}"
        # directory IO classes
        ioclass_config.add_ioclass(
            ioclass_id=ioclass_id_1,
            eviction_priority=1,
            allocation=True,
            rule=f"directory:{classified_dir_path_1}",
            ioclass_config_path=ioclass_config_path,
        )
        ioclass_config.add_ioclass(
            ioclass_id=ioclass_id_2,
            eviction_priority=1,
            allocation=True,
            rule=f"directory:{classified_dir_path_2}",
            ioclass_config_path=ioclass_config_path,
        )
        casadm.load_io_classes(cache_id=cache.cache_id, file=ioclass_config_path)

        TestProperties.LOGGER.info(f"Preparing {filesystem.name} filesystem "
                                   f"and mounting {core.system_path} at {mountpoint}")
        core.create_filesystem(fs_type=filesystem)
        core.mount(mount_point=mountpoint)
        sync()

        non_classified_dir_path = f"{mountpoint}/non_classified"
        TestProperties.LOGGER.info(
            f"Creating a non-classified directory: {non_classified_dir_path}")
        dir_1 = Directory.create_directory(path=non_classified_dir_path)

        TestProperties.LOGGER.info(f"Renaming {non_classified_dir_path} to {classified_dir_path_1}")
        dir_1.move(destination=classified_dir_path_1)

        TestProperties.LOGGER.info("Creating files with delay check")
        create_files_with_classification_delay_check(directory=dir_1, ioclass_id=ioclass_id_1)

        TestProperties.LOGGER.info(f"Creating {classified_dir_path_2}/subdir")
        dir_2 = Directory.create_directory(path=f"{classified_dir_path_2}/subdir", parents=True)

        TestProperties.LOGGER.info("Creating files with delay check")
        create_files_with_classification_delay_check(directory=dir_2, ioclass_id=ioclass_id_2)
        sync()
        drop_caches(3)

        TestProperties.LOGGER.info(f"Moving {dir_2.full_path} to {classified_dir_path_1}")
        dir_2.move(destination=classified_dir_path_1)

        TestProperties.LOGGER.info("Reading files with reclassification check")
        read_files_with_reclassification_check(
            target_ioclass_id=ioclass_id_1, source_ioclass_id=ioclass_id_2,
            directory=dir_2, with_delay=False)
        sync()
        drop_caches(3)

        TestProperties.LOGGER.info(f"Moving {dir_2.full_path} to {mountpoint}")
        dir_2.move(destination=mountpoint)

        TestProperties.LOGGER.info("Reading files with reclassification check")
        read_files_with_reclassification_check(
            target_ioclass_id=0, source_ioclass_id=ioclass_id_1,
            directory=dir_2, with_delay=False)

        TestProperties.LOGGER.info(f"Removing {classified_dir_path_2}")
        fs_utils.remove(path=classified_dir_path_2, force=True, recursive=True)
        sync()
        drop_caches(3)

        TestProperties.LOGGER.info(f"Renaming {classified_dir_path_1} to {classified_dir_path_2}")
        dir_1.move(destination=classified_dir_path_2)

        TestProperties.LOGGER.info("Reading files with reclassification check")
        read_files_with_reclassification_check(
            target_ioclass_id=ioclass_id_2, source_ioclass_id=ioclass_id_1,
            directory=dir_1, with_delay=True)

        TestProperties.LOGGER.info(f"Renaming {classified_dir_path_2} to {non_classified_dir_path}")
        dir_1.move(destination=non_classified_dir_path)

        TestProperties.LOGGER.info("Reading files with reclassification check")
        read_files_with_reclassification_check(
            target_ioclass_id=0, source_ioclass_id=ioclass_id_2,
            directory=dir_1, with_delay=True)

        core.unmount()

        ioclass_config.remove_ioclass_config(ioclass_config_path=ioclass_config_path)
        ioclass_config.create_ioclass_config(
            add_default_rule=False, ioclass_config_path=ioclass_config_path
        )
        ioclass_config.add_ioclass(
            ioclass_id=0,
            eviction_priority=22,
            allocation=False,
            rule="unclassified",
            ioclass_config_path=ioclass_config_path,
        )
