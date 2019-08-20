#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import time
from test_package.test_properties import TestProperties


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
