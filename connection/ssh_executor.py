#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import re
import time
from datetime import timedelta

import paramiko

from config.configuration import proxy_command
from connection.base_executor import BaseExecutor
from test_package.test_properties import TestProperties
from test_utils.output import Output


class SshExecutor(BaseExecutor):
    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.ssh = paramiko.SSHClient()
        self.connect(username, password, port)
        # self.channel = self.ssh.invoke_shell()
        # self.stdin = self.channel.makefile('wb')
        # self.stdout = self.channel.makefile('rb')
        # self.prompt = None
        # self.execute("", timedelta(seconds=3))  # empty command to initialize and check connection

    def __del__(self):
        self.ssh.close()

    def connect(self, user, passwd, port, timeout: timedelta = timedelta(seconds=30)):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.ssh.connect(self.ip, username=user, password=passwd,
                             port=port, timeout=timeout.total_seconds())
        except paramiko.SSHException:
            raise ConnectionError(f"An exception occurred while trying to connect to {self.ip}")

    def disconnect(self):
        try:
            self.ssh.close()
        except Exception:
            raise Exception(f"An exception occurred while trying to disconnect from {self.ip}")

    def execute(self, command, timeout: timedelta = timedelta(hours=1)):
        try:
            (stdin, stdout, stderr) = self.ssh.exec_command(command,
                                                            timeout=timeout.total_seconds())
        except paramiko.SSHException as e:
            raise ConnectionError(f"An exception occurred while executing command {command} on"
                                  f" {self.ip}\n{e}")

        return Output(stdout, stderr, stdout.channel.recv_exit_status())

    def execute_with_proxy(self, command, timeout: timedelta = timedelta(hours=1)):
        if proxy_command:
            command = f"{proxy_command} && {command}"
        try:
            (stdin, stdout, stderr) = self.ssh.exec_command(command,
                                                            timeout=timeout.total_seconds())
        except paramiko.SSHException as e:
            raise ConnectionError(f"An exception occurred while executing command {command} on"
                                  f" {self.ip}\n{e}")

        return Output(stdout, stderr, stdout.channel.recv_exit_status())

    def execute_old(self, command, timeout: timedelta = timedelta(hours=1)):
        self.stdin.write(command + '\n')
        echo_cmd = f'echo __exit_code: $?'
        self.stdin.write(echo_cmd + '\n')
        self.stdin.flush()
        result = Output([], "", 0)

        start = time.time()

        n_bytes = 0
        exit_code_received = False
        echo_cmd_displayed = False
        cmd_displayed = False
        while not exit_code_received and time.time() - start < timeout.seconds:
            # Some remote environments do not send properly ended output
            # which results in hang when using readline(). Reading bytes instead
            # allows to read output properly.
            n_bytes_next = len(self.stdout.channel.in_buffer)
            if n_bytes_next == 0:
                continue
            if n_bytes_next > n_bytes:
                n_bytes = n_bytes_next
                time.sleep(0.04)
                continue

            stdout = self.stdout.read(n_bytes)
            for line in stdout.split(b'\r\n'):  # splitlines() splits on '\r' which is not desired
                line = line.decode("utf-8")
                if not cmd_displayed:  # Virtual terminal adds ' \r' every 80 characters in input
                    line = line.replace(' \r', '')
                if re.match(r'__exit_code: \d+', line):  # Read exit code
                    result.exit_code = int(line.split()[-1])
                    exit_code_received = True
                    break
                elif line.endswith(echo_cmd):
                    echo_cmd_displayed = True
                    if command == "" and self.prompt is None:
                        self.prompt = line.replace(echo_cmd, '').strip()
                        if self.prompt == "":
                            self.prompt = None
                    elif self.prompt is not None:
                        sub_line = line.replace(echo_cmd, '').replace(self.prompt, '').strip()
                        if len(sub_line) != 0:
                            result.stdout.append(self.clean_line(sub_line))
                elif command == "" and line == "":
                    continue
                elif line == command:  # Input command displayed
                    cmd_displayed = True
                    result.stdout = []
                elif '__exit_code' not in line and \
                        not line.replace(' \r', '').strip().endswith(command):  # Proper output
                    result.stdout.append(self.clean_line(line))
            n_bytes = 0

        if not exit_code_received:
            if echo_cmd_displayed:
                TestProperties.LOGGER.warn("No exit code received")
            else:
                raise TimeoutError(f"SSH command '{command}' has timed out after {timeout}")

        if result.stdout:
            result.stdout = '\n'.join(result.stdout)
        else:
            result.stdout = ""
        if result.exit_code:
            result.stderr = result.stdout
            result.stdout = ""

        return result

    def execute_in_background(self, command, timeout: timedelta = timedelta(hours=1)):
        command += "&> /dev/null &"
        output = self.execute(command, timeout)

        pid = output.stdout.split()[1]

        return pid

    @staticmethod
    def wait_cmd_finish(pid: int):
        output = TestProperties.executor.execute(f"wait {pid}")
        if output.exit_code != 0:
            raise ValueError(f"Unable to wait for process with pid {pid}")

    @staticmethod
    def clean_line(line):
        return re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]').sub('', line) \
            .replace('\b', '') \
            .replace('\r', '') \
            .replace('\n', '')
