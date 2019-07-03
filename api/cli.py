#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging

LOGGER = logging.getLogger(__name__)

casadm_bin = "casadm"


def add_core_cmd(cache_id: int, core_dev: str, core_id: int = None, shortcut: bool = False):
    command = f" -A -i {str(cache_id)} -d {core_dev}" if shortcut \
        else f" --add-core --cache-id {str(cache_id)} --core-device {core_dev}"
    if core_id is not None:
        command += + " -j " + str(core_id) if shortcut else " --core-id " + str(core_id)
    LOGGER.info(casadm_bin + command)
    return casadm_bin + command


def remove_core_cmd(cache_id: int, core_id: int, force: bool = False, shortcut: bool = False):
    command = f" -R -i {cache_id} -j {core_id}" if shortcut \
        else f" --remove-core --cache-id {cache_id} --core-id {core_id}"
    if force:
        command += " -f" if shortcut else " --force"
    return casadm_bin + command


def help_cmd(shortcut: bool = False):
    return casadm_bin + " -H" if shortcut else casadm_bin + " --help"


def start_cmd(cache_dev: str, cache_mode=None, cache_line_size=None,
              cache_id=None, force=False, load=False, shortcut=False):
    command = " -S" if shortcut else " --start-cache"
    command += " -d " + cache_dev if shortcut else " --cache-device " + cache_dev
    if cache_mode is not None:
        command += " -c " + cache_mode if shortcut else " --cache-mode " + cache_mode
    if cache_line_size is not None:
        command += " -x " + str(cache_line_size) if shortcut \
            else " --cache-line-size " + str(cache_line_size)
    if cache_id is not None:
        command += " -i " + str(cache_id) if shortcut else " --cache-id " + str(cache_id)
    if force:
        command += " -f" if shortcut else " --force"
    if load:
        command += " -l" if shortcut else " --load"
    return casadm_bin + command


def stop_cmd(cache_id: int, no_data_flush: bool = False, shortcut: bool = False):
    command = " -T " if shortcut else " --stop-cache"
    command += " -i " + str(cache_id) if shortcut else " --cache-id " + str(cache_id)
    if no_data_flush:
        command += " --no-data-flush"
    return casadm_bin + command


def list_cmd(output_format: str = None, shortcut: bool = False):
    command = " -L" if shortcut else " --list-caches"
    if output_format == "table" or output_format == "csv":
        command += " -o " + output_format if shortcut else " --output-format " + output_format
    return casadm_bin + command


def load_cmd(cache_dev: str, shortcut: bool = False):
    return start_cmd(cache_dev, load=True, shortcut=shortcut)
