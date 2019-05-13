#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from connection import base_executor
import logging
from config import configuration

LOGGER = logging.getLogger(__name__)

opencas_repo_name = "open-cas-linux"


def install_opencas(executor: base_executor.BaseExecutor):
    LOGGER.info("Cloning Open CAS repository.")
    executor.execute(configuration.proxy_command)
    executor.execute(f"cd {configuration.opencas_repo_path}")
    executor.execute(f"if [ -d {opencas_repo_name} ]; then rm -rf {opencas_repo_name}; fi")
    output = executor.execute("git clone --recursive https://github.com/Open-CAS/open-cas-linux.git")
    if output.exit_code != 0:
        raise Exception(f"Error while cloning repository: {output.stdout}\n{output.stderr}")

    LOGGER.info("Open CAS make and make install.")
    output = executor.execute("cd open-cas-linux/ && ./configure && make")
    if output.exit_code != 0:
        raise Exception(f"Make command executed with nonzero status: {output.stdout}\n{output.stderr}")

    output = executor.execute("make install")
    if output.exit_code != 0:
        raise Exception(f"Error while installing Open CAS: {output.stdout}\n{output.stderr}")

    LOGGER.info("Check if casadm is properly installed.")
    output = executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception("'casadm -V' command returned an error: {output.stdout}\n{output.stderr}")
    else:
        LOGGER.info(output.stdout)


def uninstall_opencas(executor: base_executor.BaseExecutor):
    LOGGER.info("Uninstalling Open CAS.")
    output = executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception("Open CAS is not properly installed.")
    else:
        executor.execute(f"cd {configuration.opencas_repo_path}/{opencas_repo_name}")
        output = executor.execute("make uninstall")
        if output.exit_code != 0:
            raise Exception(f"There was an error during uninstall process: {output.stdout}\n{output.stderr}")
