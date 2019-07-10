#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from .casctl import stop as casctl_stop
from test_package.test_properties import TestProperties
from enum import Enum
from cas_configuration.cache_config import CacheLineSize, CacheMode
from utils.size import Size, Unit


class OutputFormat(Enum):
    table = "table"
    csv = "csv"


class StatsFilter(Enum):
    all = "all"
    conf = "conf"
    usage = "usage"
    req = "req"
    blk = "blk"
    err = "err"


def help(shortcut: bool = False):
    return TestProperties.executor.execute(help_cmd(shortcut))


# TODO:In the future cache_dev will probably be more complex than string value
def start_cache(cache_dev: str, cache_mode: CacheMode = None,
                cache_line_size: CacheLineSize = None, cache_id: int = None,
                force: bool = False, load: bool = False, shortcut: bool = False):
    cls = None if cache_line_size is None else str(CacheLineSize.get_value(Unit.KibiByte))
    id = None if cache_id is None else str(cache_id)
    output = TestProperties.executor.execute(start_cmd(
        cache_dev, cache_mode, cls, id, force, load, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to start cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def stop_cache(cache_id: int, no_data_flush: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(stop_cmd(str(cache_id), no_data_flush, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to stop cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def add_core(cache_id: int, core_dev: str, core_id: int = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(id)
    output = TestProperties.executor.execute(
        add_core_cmd(str(cache_id), core_dev, _core_id, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to add core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def remove_core(cache_id: int, core_id: int, force: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(
        remove_core_cmd(str(cache_id), str(core_id), force, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to remove core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def remove_detached(core_device: str, shortcut: bool = False):
    output = TestProperties.executor.execute(remove_detached_cmd(core_device, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to remove detached core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def reset_counters(cache_id: int, core_id: int = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(core_id)
    output = TestProperties.executor.execute(reset_counters(str(cache_id), _core_id, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to reset counters. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def flush(cache_id: int, core_id: int = None, shortcut: bool = False):
    command = flush_cache_cmd(str(cache_id), shortcut) if core_id is None \
         else flush_core_cmd(str(cache_id), str(core_id), shortcut)
    output = TestProperties.executor.execute(command)
    if output.exit_code != 0:
        raise Exception(
            f"Flushing failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def load_cache(cache_dev: str, shortcut: bool = False):
    output = TestProperties.executor.execute(load_cmd(cache_dev, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to load cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def list_caches(output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(list_cmd(output_format, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to list caches. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def print_version(output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(version_cmd(output_format, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to print version. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def format_nvme(cache_dev: str, force: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(format_cmd(cache_dev, force, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Format command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def stop_all_caches():
    if "No caches running" in list_caches().stdout:
        return
    LOGGER.info("Stop all caches")
    casctl_stop()
    output = list_caches()
    if "No caches running" not in output.stdout:
        raise Exception(
            f"Error while stopping caches. stdout: {output.stdout} \n stderr :{output.stderr}")


def parse_list_caches():
    parsed_output = {"caches": {}, "cores": {}}
    lines = list_caches("csv").stdout.split('\n')
    for line in lines:
        args = line.split(',')
        if args[0] == "cache":
            parsed_output["caches"] =\
                {args[1]: {"path": args[2], "state": args[3], "mode": args[4]}}
        elif args[0] == "core":
            parsed_output["cores"] = \
                {args[1]: {"path": args[2], "state": args[3], "device": args[5]}}
    return parsed_output


def print_statistics(cache_id: int, core_id: int = None, per_io_class: bool = False,
                     io_class_id: int = None, filter: StatsFilter = None,
                     output_format: OutputFormat = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(core_id)
    _io_class_id = None if io_class_id is None else str(io_class_id)
    output = TestProperties.executor.execute(
        print_statistics_cmd(
            str(cache_id), _core_id, per_io_class, _io_class_id, filter, output_format, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Format command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_cache_mode(cache_mode: CacheMode, cache_id: int,
                   flush: bool = True, shortcut: bool = False):
    flush_cache = None
    if cache_mode in [CacheMode.WB, CacheMode.WO]:
        flush_cache = "yes" if flush else "no"

    output = TestProperties.executor.execute(
        set_cache_mode_cmd(cache_mode, str(cache_id), flush_cache, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Set cache mode command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def load_io_classes(cache_id: int, file: str, shortcut: bool = False):
    output = TestProperties.executor.execute(load_io_classes_cmd(str(cache_id), file, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Load ioclass command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def list_io_classes(cache_id: int, output_format: OutputFormat, shortcut: bool = False):
    output = TestProperties.executor.execute(
        list_io_classes_cmd(str(cache_id), output_format, shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"List ioclass command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output
