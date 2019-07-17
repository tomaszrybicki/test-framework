#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from .cli import *
from .casctl import stop as casctl_stop
from test_package.test_properties import TestProperties
from enum import Enum
from cas_configuration.cache_config import CacheLineSize, CacheMode, SeqCutOffPolicy, CleaningPolicy
from test_utils.size import Size, Unit
from typing import List


class OutputFormat(Enum):
    table = 0
    csv = 1


class StatsFilter(Enum):
    all = 0
    conf = 1
    usage = 2
    req = 3
    blk = 4
    err = 5


def help(shortcut: bool = False):
    return TestProperties.executor.execute(help_cmd(shortcut))


# TODO:In the future cache_dev will probably be more complex than string value
def start_cache(cache_dev: str, cache_mode: CacheMode = None,
                cache_line_size: CacheLineSize = None, cache_id: int = None,
                force: bool = False, load: bool = False, shortcut: bool = False):
    _cache_line_size = None if cache_line_size is None else str(
        CacheLineSize.get_value(Unit.KibiByte))
    _cache_id = None if cache_id is None else str(cache_id)
    output = TestProperties.executor.execute(start_cmd(
        cache_dev=cache_dev, cache_mode=cache_mode.name, cache_line_size=_cache_line_size,
        cache_id=_cache_id, force=force, load=load, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to start cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def stop_cache(cache_id: int, no_data_flush: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(
        stop_cmd(cache_id=str(cache_id), no_data_flush=no_data_flush, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to stop cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def add_core(cache_id: int, core_dev: str, core_id: int = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(id)
    output = TestProperties.executor.execute(
        add_core_cmd(cache_id=str(cache_id), core_dev=core_dev,
                     core_id=_core_id, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to add core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def remove_core(cache_id: int, core_id: int, force: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(
        remove_core_cmd(cache_id=str(cache_id), core_id=str(core_id),
                        force=force, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to remove core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def remove_detached(core_device: str, shortcut: bool = False):
    output = TestProperties.executor.execute(
        remove_detached_cmd(core_device=core_device, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to remove detached core. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def reset_counters(cache_id: int, core_id: int = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(core_id)
    output = TestProperties.executor.execute(
        reset_counters_cmd(cache_id=str(cache_id), core_id=_core_id, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to reset counters. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def flush(cache_id: int, core_id: int = None, shortcut: bool = False):
    if core_id is None:
        command = flush_cache_cmd(cache_id=str(cache_id), shortcut=shortcut)
    else:
        command = flush_core_cmd(cache_id=str(cache_id), core_id=str(core_id), shortcut=shortcut)
    output = TestProperties.executor.execute(command)
    if output.exit_code != 0:
        raise Exception(
            f"Flushing failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def load_cache(cache_dev: str, shortcut: bool = False):
    output = TestProperties.executor.execute(load_cmd(cache_dev=cache_dev, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to load cache. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def list_caches(output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(
        list_cmd(output_format=output_format.name, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to list caches. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def print_version(output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(
        version_cmd(output_format=output_format.name, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Failed to print version. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def format_nvme(cache_dev: str, force: bool = False, shortcut: bool = False):
    output = TestProperties.executor.execute(
        format_cmd(cache_dev=cache_dev, force=force, shortcut=shortcut))
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
    lines = list_caches(OutputFormat.csv).stdout.split('\n')
    for line in lines:
        args = line.split(',')
        if args[0] == "cache":
            parsed_output["caches"][args[1]] = {"path": args[2], "state": args[3], "mode": args[4]}
        elif args[0] == "core":
            parsed_output["cores"][args[5]] = \
                {"path": args[2], "id": args[1], "state": args[3], "device": args[5]}
    return parsed_output


def print_statistics(cache_id: int, core_id: int = None, per_io_class: bool = False,
                     io_class_id: int = None, filter: List[StatsFilter] = None,
                     output_format: OutputFormat = None, shortcut: bool = False):
    _core_id = None if core_id is None else str(core_id)
    _io_class_id = None if io_class_id is None else str(io_class_id)
    if filter is None:
        _filter = filter
    else:
        names = (x.name for x in filter)
        _filter = ",".join(names)
    output = TestProperties.executor.execute(
        print_statistics_cmd(
            cache_id=str(cache_id), core_id=_core_id,
            per_io_class=per_io_class, io_class_id=_io_class_id,
            filter=filter, output_format=output_format.name, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Printing statistics failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_cache_mode(cache_mode: CacheMode, cache_id: int,
                   flush: bool = True, shortcut: bool = False):
    flush_cache = None
    if cache_mode in [CacheMode.WB, CacheMode.WO]:
        flush_cache = "yes" if flush else "no"

    output = TestProperties.executor.execute(
        set_cache_mode_cmd(cache_mode=cache_mode.name, cache_id=str(cache_id),
                           flush_cache=flush_cache, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Set cache mode command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def load_io_classes(cache_id: int, file: str, shortcut: bool = False):
    output = TestProperties.executor.execute(
        load_io_classes_cmd(cache_id=str(cache_id), file=file, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Load IO class command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def list_io_classes(cache_id: int, output_format: OutputFormat, shortcut: bool = False):
    output = TestProperties.executor.execute(
        list_io_classes_cmd(cache_id=str(cache_id),
                            output_format=output_format.name, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"List IO class command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def get_param_cutoff(cache_id: int, core_id: int,
                     output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(
        get_param_cutoff_cmd(cache_id=str(cache_id), core_id=str(core_id),
                             output_format=output_format.name, shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Getting sequential cutoff params failed."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def get_param_cleaning(cache_id: int, output_format: OutputFormat = None, shortcut: bool = False):
    output = TestProperties.executor.execute(
        get_param_cleaning_cmd(cache_id=str(cache_id), output_format=output_format.name,
                               shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Getting cleaning policy params failed."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def get_param_cleaning_alru(cache_id: int, output_format: OutputFormat = None,
                            shortcut: bool = False):
    output = TestProperties.executor.execute(
        get_param_cleaning_alru_cmd(cache_id=str(cache_id), output_format=output_format.name,
                                    shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Getting alru cleaning policy params failed."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def get_param_cleaning_acp(cache_id: int, output_format: OutputFormat = None,
                           shortcut: bool = False):
    output = TestProperties.executor.execute(
        get_param_cleaning_acp_cmd(cache_id=str(cache_id), output_format=output_format.name,
                                   shortcut=shortcut))
    if output.exit_code != 0:
        raise Exception(
            f"Getting acp cleaning policy params failed."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_param_cutoff(cache_id: int, core_id: int = None, threshold: Size = None,
                     policy: SeqCutOffPolicy = None):
    _threshold = None if threshold is None else threshold.get_value(Unit.KibiByte)
    if core_id is None:
        command = set_param_cutoff_cmd(
            cache_id=str(cache_id), threshold=_threshold,
            policy=policy.name)
    else:
        command = set_param_cutoff_cmd(
            cache_id=str(cache_id), core_id=str(core_id),
            threshold=_threshold, policy=policy.name)
    output = TestProperties.executor.execute(command)
    if output.exit_code != 0:
        raise Exception(
            f"Error while setting sequential cut-off params."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_param_cleaning(cache_id: int, policy: CleaningPolicy):
    output = TestProperties.executor.execute(
        set_param_cleaning_cmd(cache_id=str(cache_id), policy=policy.name))
    if output.exit_code != 0:
        raise Exception(
            f"Error while setting cleaning policy."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_param_cleaning_alru(cache_id: int, wake_up: int = None, staleness_time: int = None,
                            flush_max_buffers: int = None, activity_threshold: int = None):
    output = TestProperties.executor.execute(
        set_param_cleaning_alru_cmd(
            cache_id=str(cache_id), wake_up=str(wake_up), staleness_time=str(staleness_time),
            flush_max_buffers=str(flush_max_buffers), activity_threshold=str(activity_threshold)))
    if output.exit_code != 0:
        raise Exception(
            f"Error while setting alru cleaning policy parameters."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output


def set_param_cleaning_acp(cache_id: int, wake_up: int = None, flush_max_buffers: int = None):
    output = TestProperties.executor.execute(
        set_param_cleaning_acp_cmd(cache_id=str(cache_id), wake_up=str(wake_up),
                                   flush_max_buffers=str(flush_max_buffers)))
    if output.exit_code != 0:
        raise Exception(
            f"Error while setting acp cleaning policy parameters."
            f" stdout: {output.stdout} \n stderr :{output.stderr}")
    return output
