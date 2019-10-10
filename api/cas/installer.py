#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import logging

from test_package import conftest
from test_package.test_properties import TestProperties

LOGGER = logging.getLogger(__name__)

opencas_repo_name = "open-cas-linux"


def install_opencas():
    LOGGER.info("Cloning Open CAS repository.")
    TestProperties.executor.execute(f"if [ -d {opencas_repo_name} ]; "
                                    f"then rm -rf {opencas_repo_name}; fi")
    output = TestProperties.executor.execute_with_proxy(
        "git clone --recursive https://github.com/Open-CAS/open-cas-linux.git")
    if output.exit_code != 0:
        raise Exception(f"Error while cloning repository: {output.stdout}\n{output.stderr}")

    output = TestProperties.executor.execute_with_proxy(
        f"cd {opencas_repo_name} && "
        f"git fetch --all && "
        f"git fetch --tags {conftest.get_remote()} +refs/pull/*:refs/remotes/origin/pr/*")
    if output.exit_code != 0:
        raise Exception(
            f"Failed to fetch: "
            f"{output.stdout}\n{output.stderr}")

    output = TestProperties.executor.execute_with_proxy(f"cd {opencas_repo_name} && "
                                                        f"git checkout {conftest.get_branch()}")
    if output.exit_code != 0:
        raise Exception(
            f"Failed to checkout to {conftest.get_branch()}: {output.stdout}\n{output.stderr}")

    LOGGER.info("Open CAS make and make install.")
    output = TestProperties.executor.execute_with_proxy(
        f"cd {opencas_repo_name} && "
        "git submodule update --init --recursive && "
        "./configure && "
        "make -j")
    if output.exit_code != 0:
        raise Exception(
            f"Make command executed with nonzero status: {output.stdout}\n{output.stderr}")

    output = TestProperties.executor.execute(f"cd {opencas_repo_name} && "
                                             f"make install")
    if output.exit_code != 0:
        raise Exception(
            f"Error while installing Open CAS: {output.stdout}\n{output.stderr}")

    LOGGER.info("Check if casadm is properly installed.")
    output = TestProperties.executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception(
            f"'casadm -V' command returned an error: {output.stdout}\n{output.stderr}")
    else:
        LOGGER.info(output.stdout)


def uninstall_opencas():
    LOGGER.info("Uninstalling Open CAS.")
    output = TestProperties.executor.execute("casadm -V")
    if output.exit_code != 0:
        raise Exception("Open CAS is not properly installed.")
    else:
        TestProperties.executor.execute(f"cd {opencas_repo_name} && "
                                        f"make uninstall")
        if output.exit_code != 0:
            raise Exception(
                f"There was an error during uninstall process: {output.stdout}\n{output.stderr}")


def reinstall_opencas():
    if check_if_installed():
        uninstall_opencas()
    install_opencas()


def check_if_installed():
    LOGGER.info("Check if Open-CAS-Linux is installed.")
    output = TestProperties.executor.execute("which casadm")
    if output.exit_code == 0:
        LOGGER.info("CAS is installed")

        return True
    LOGGER.info("CAS not installed")
    return False
