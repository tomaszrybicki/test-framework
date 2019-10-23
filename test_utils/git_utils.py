#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

from core.test_run import TestRun
from api.cas.installer import opencas_repo_name


def get_current_commit_hash():
    return TestRun.executor.run(
        f'cd {opencas_repo_name} && git show HEAD --pretty=format:"%H"').stdout


def get_current_commit_message():
    return TestRun.executor.run(
        f'cd {opencas_repo_name} && git show HEAD --pretty=format:"%s"').stdout
