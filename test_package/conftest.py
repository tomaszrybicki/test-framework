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
sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir))

# User should provide config/configuration.py with path to own test_wrapper,
# or in case there is no test_wrapper, add blank path.
import config.configuration as c
from connection.ssh_executor import SshExecutor
from connection.local_executor import LocalExecutor
from test_package.test_properties import TestProperties
from utils.dut import Dut
if os.path.exists(c.test_wrapper_dir):
    sys.path.append(os.path.abspath(c.test_wrapper_dir))
    import test_wrapper
from installers import installer as installer

LOGGER = logging.getLogger(__name__)


@pytest.fixture()
def prepare_and_cleanup(request):
    """
    This fixture returns the dictionary, which contains DUT ip, IPMI, spider, list of disks.
    This fixture also returns the executor of commands
    """

    # There should be dut config file added to config package and
    # pytest should be executed with option --config=conf_name'.
    #
    # 'ip' field should be filled with valid IP string to use remote ssh executor
    # or it should be commented out when user want to execute tests on local machine
    #
    # User can also have own test wrapper, which runs test prepare, cleanup, etc.
    # Then in the config/configuration.py file there should be added path to it:
    # test_wrapper_dir = 'wrapper_path'

    try:
        dut_config = importlib.import_module(f"config.{request.config.option.config}")
    except:
        dut_config = None

    if os.path.exists(c.test_wrapper_dir):
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        yield from test_wrapper.run_test_wrapper(request, dut_config)
    elif dut_config is not None:
        if hasattr(dut_config, 'ip'):
            try:
                IP(dut_config.ip)
                yield {'ip': dut_config.ip, 'disks': dut_config.disks}, \
                    SshExecutor(dut_config.ip, dut_config.user, dut_config.password)
            except ValueError:
                raise Exception("IP address from configuration file is in invalid format.")
        else:
            yield {'disks': dut_config.disks}, LocalExecutor()
    else:
        raise Exception(
            "There is neither configuration file nor test wrapper attached to tests execution.")


def pytest_addoption(parser):
    parser.addoption("--config", action="store", default="config/configuration.py")
    parser.addoption("--repo-tag", action="store", default="master")


def base_prepare(prepare_fixture):
    LOGGER.info("Base test prepare")
    LOGGER.info("Initializing executor and dut information")
    dut_info, executor = prepare_fixture
    TestProperties.executor = executor
    TestProperties.dut = Dut(dut_info)
    LOGGER.info(f"DUT info: {TestProperties.dut}")
    if c.force_update and not hasattr(c, "already_updated"):
        installer.reinstall_opencas()
    elif not installer.check_if_installed():
        installer.install_opencas()
    c.already_updated = True  # to skip reinstall every test
