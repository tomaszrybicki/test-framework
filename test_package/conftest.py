#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import logging
import pytest
import os
import sys
import importlib
from IPy import IP
from test_utils import disk_finder
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

# User should provide config/configuration.py with path to own test_wrapper,
# or in case there is no test_wrapper, add blank path.
import config.configuration as c
from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from core.test_run import TestRun
from test_utils.dut import Dut
if os.path.exists(c.test_wrapper_dir):
    sys.path.append(os.path.abspath(c.test_wrapper_dir))
    import test_wrapper
from api.cas import installer
from api.cas import casadm
from test_utils.os_utils import Udev

LOGGER = logging.getLogger(__name__)


pytest_options = {}


@pytest.fixture(scope="session", autouse=True)
def get_pytest_options(request):
    pytest_options["remote"] = request.config.getoption("--remote")
    pytest_options["branch"] = request.config.getoption("--repo-tag")
    pytest_options["force_reinstall"] = request.config.getoption("--force-reinstall")


@pytest.fixture()
def prepare_and_cleanup(request):
    """
    This fixture returns the dictionary, which contains DUT ip, IPMI, spider, list of disks.
    This fixture also returns the executor of commands
    """

    # There should be dut config file added to config package and
    # pytest should be executed with option --dut-config=conf_name'.
    #
    # 'ip' field should be filled with valid IP string to use remote ssh executor
    # or it should be commented out when user want to execute tests on local machine
    #
    # User can also have own test wrapper, which runs test prepare, cleanup, etc.
    # Then in the config/configuration.py file there should be added path to it:
    # test_wrapper_dir = 'wrapper_path'
    LOGGER.info(f"**********Test {request.node.name} started!**********")
    try:
        dut_config = importlib.import_module(f"config.{request.config.getoption('--dut-config')}")
    except:
        dut_config = None

    if os.path.exists(c.test_wrapper_dir):
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        TestRun.dut = Dut(test_wrapper.prepare(request, dut_config))
    elif dut_config is not None:
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
                if hasattr(dut_config, 'user') and hasattr(dut_config, 'password'):
                    executor = SshExecutor(dut_config.ip, dut_config.user, dut_config.password)
                    TestRun.executor = executor
                else:
                    raise Exception("There is no credentials in config file.")
                if hasattr(dut_config, 'disks'):
                    TestRun.dut = Dut({'ip': dut_config.ip, 'disks': dut_config.disks})
                else:
                    TestRun.dut = Dut(
                        {'ip': dut_config.ip, 'disks': disk_finder.find_disks()})
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        elif hasattr(dut_config, 'disks'):
            TestRun.executor = LocalExecutor()
            TestRun.dut = Dut({'disks': dut_config.disks})
        else:
            TestRun.executor = LocalExecutor()
            TestRun.dut = Dut({'disks': disk_finder.find_disks()})
    else:
        raise Exception(
            "There is neither configuration file nor test wrapper attached to tests execution.")
    yield
    TestRun.LOGGER.info("Test cleanup")
    Udev.enable()
    unmount_cas_devices()
    casadm.stop_all_caches()
    if os.path.exists(c.test_wrapper_dir):
        test_wrapper.cleanup(TestRun.dut)


def pytest_addoption(parser):
    parser.addoption("--dut-config", action="store", default="None")
    parser.addoption("--remote", action="store", default="origin")
    parser.addoption("--repo-tag", action="store", default="master")
    parser.addoption("--force-reinstall", action="store", default="False")
    # TODO: investigate whether it is possible to pass the last param as bool


def get_remote():
    return pytest_options["remote"]


def get_branch():
    return pytest_options["branch"]


def get_force_param():
    return pytest_options["force_reinstall"]


def unmount_cas_devices():
    output = TestRun.executor.execute("cat /proc/mounts | grep cas")
    # If exit code is '1' but stdout is empty, there is no mounted cas devices
    if output.exit_code == 1:
        return
    elif output.exit_code != 0:
        raise Exception(
            f"Failed to list mounted cas devices. \
            stdout: {output.stdout} \n stderr :{output.stderr}"
        )

    for line in output.stdout.splitlines():
        cas_device_path = line.split()[0]
        TestRun.LOGGER.info(f"Unmounting {cas_device_path}")
        output = TestRun.executor.execute(f"umount {cas_device_path}")
        if output.exit_code != 0:
            raise Exception(
                f"Failed to unmount {cas_device_path}. \
                stdout: {output.stdout} \n stderr :{output.stderr}"
            )


def kill_all_io():
    TestRun.executor.execute("pkill --signal SIGKILL dd")
    TestRun.executor.execute("kill -9 `ps aux | grep -i vdbench.* | awk '{ print $1 }'`")
    TestRun.executor.execute("pkill --signal SIGKILL fio*")


def base_prepare():
    LOGGER.info("Base test prepare")
    LOGGER.info(f"DUT info: {TestRun.dut}")

    Udev.enable()

    kill_all_io()

    if installer.check_if_installed():
        try:
            unmount_cas_devices()
            casadm.stop_all_caches()
        except Exception:
            pass  # TODO: Reboot DUT if test is executed remotely
    for disk in TestRun.dut.disks:
        if disk.is_mounted():
            disk.unmount()
        disk.remove_partitions()

    if get_force_param() is not "False" and not hasattr(c, "already_updated"):
        installer.reinstall_opencas()
    elif not installer.check_if_installed():
        installer.install_opencas()
    c.already_updated = True  # to skip reinstall every test
