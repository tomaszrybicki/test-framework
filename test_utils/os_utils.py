#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time

from aenum import Enum

from test_package.test_properties import TestProperties
from test_utils.filesystem.file import File


class Udev(object):
    @staticmethod
    def enable():
        TestProperties.LOGGER.info("Enabling udev")
        output = TestProperties.executor.execute("udevadm control --start-exec-queue")
        if output.exit_code != 0:
            raise Exception(
                f"Enabling udev failed. stdout: {output.stdout} \n stderr :{output.stderr}"
            )

    @staticmethod
    def disable():
        TestProperties.LOGGER.info("Disabling udev")
        output = TestProperties.executor.execute("udevadm control --stop-exec-queue")
        if output.exit_code != 0:
            raise Exception(
                f"Disabling udev failed. stdout: {output.stdout} \n stderr :{output.stderr}"
            )


def download_file(url, destination_dir="/tmp"):
    command = ("wget --tries=3 --timeout=5 --continue --quiet "
               f"--directory-prefix={destination_dir} {url}")
    output = TestProperties.executor.execute_with_proxy(command)
    if output.exit_code != 0:
        raise Exception(
            f"Download failed. stdout: {output.stdout} \n stderr :{output.stderr}")
    path = f"{destination_dir.rstrip('/')}/{File.get_name(url)}"
    return File(path)


class ModuleRemoveMethod(Enum):
    rmmod = "rmmod"
    modprobe = "modprobe -r"


def is_kernel_module_loaded(module_name):
    output = TestProperties.executor.execute(f"lsmod | grep ^{module_name}")
    return output.exit_code == 0


def load_kernel_module(module_name, module_args: {str, str}=None):
    cmd = f"modprobe {module_name}"
    if module_args is not None:
        for key, value in module_args.items():
            cmd += f" {key}={value}"
    return TestProperties.executor.execute(cmd)


def unload_kernel_module(module_name, unload_method: ModuleRemoveMethod = ModuleRemoveMethod.rmmod):
    cmd = f"{unload_method.value} {module_name}"
    return TestProperties.executor.execute(cmd)


def reload_kernel_module(module_name, module_args: {str, str}=None):
    unload_kernel_module(module_name)
    time.sleep(1)
    load_kernel_module(module_name, module_args)


def wait(predicate, timeout, interval=None):
    start = time.time()
    result = False
    while time.time() - start < timeout:
        result = predicate()
        if result:
            break
        if interval is not None:
            time.sleep(interval)
    return result


def sync():
    output = TestProperties.executor.execute("sync")
    if output.exit_code != 0:
        raise Exception(
            f"Sync command failed. stdout: {output.stdout} \n stderr :{output.stderr}")
