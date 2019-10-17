#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import base64
import textwrap
from datetime import datetime

from aenum import IntFlag, Enum

from core.test_run import TestRun
from test_utils.size import Size, Unit


class Permissions(IntFlag):
    r = 4
    w = 2
    x = 1

    def __str__(self):
        ret_string = ""
        for p in Permissions:
            if p in self:
                ret_string += p.name
        return ret_string


class PermissionsUsers(IntFlag):
    u = 4
    g = 2
    o = 1

    def __str__(self):
        ret_string = ""
        for p in PermissionsUsers:
            if p in self:
                ret_string += p.name
        return ret_string


class PermissionSign(Enum):
    add = '+'
    remove = '-'
    set = '='


def create_directory(path, parents: bool = False):
    cmd = f"mkdir {'--parents ' if parents else ''}{path}"
    return TestRun.executor.run_expect_success(cmd)


def check_if_directory_exists(path):
    return TestRun.executor.run(f"test -d {path}").exit_code == 0


def check_if_file_exists(path):
    return TestRun.executor.run(f"test -e {path}").exit_code == 0


def copy(source: str,
         destination: str,
         force: bool = False,
         recursive: bool = False,
         dereference: bool = False):
    cmd = f"cp{' --force' if force else ''}" \
        f"{' --recursive' if recursive else ''}" \
        f"{' --dereference' if dereference else ''} " \
        f"{source} {destination}"
    return TestRun.executor.run_expect_success(cmd)


def move(source, destination, force: bool = False):
    cmd = f"mv{' --force' if force else ''} {source} {destination}"
    return TestRun.executor.run_expect_success(cmd)


def remove(path, force: bool = False, recursive: bool = False, ignore_errors: bool = False):
    cmd = f"rm{' --force' if force else ''}{' --recursive' if recursive else ''} {path}"
    output = TestRun.executor.run(cmd)
    if output.exit_code != 0 and not ignore_errors:
        raise Exception(f"Could not remove file {path}."
                        f"\nstdout: {output.stdout}\nstderr: {output.stderr}")
    return output


def chmod(path, permissions: Permissions, users: PermissionsUsers,
          sign: PermissionSign = PermissionSign.set, recursive: bool = False):
    cmd = f"chmod{' --recursive' if recursive else ''} " \
        f"{str(users)}{sign.value}{str(permissions)} {path}"
    output = TestRun.executor.run(cmd)
    return output


def chmod_numerical(path, permissions: int, recursive: bool = False):
    cmd = f"chmod{' --recursive' if recursive else ''} {permissions} {path}"
    return TestRun.executor.run_expect_success(cmd)


def chown(path, owner, group, recursive):
    cmd = f"chown {'--recursive ' if recursive else ''}{owner}:{group} {path}"
    return TestRun.executor.run_expect_success(cmd)


def create_file(path):
    if not path.strip():
        raise ValueError("Path cannot be empty or whitespaces.")
    cmd = f"touch '{path}'"
    return TestRun.executor.run_expect_success(cmd)


def compare(file, other_file):
    output = TestRun.executor.run(
        f"cmp --silent {file} {other_file}")
    if output.exit_code == 0:
        return True
    elif output.exit_code > 1:
        raise Exception(f"Compare command execution failed. {output.stdout}\n{output.stderr}")
    else:
        return False


def diff(file, other_file):
    output = TestRun.executor.run(
        f"diff {file} {other_file}")
    if output.exit_code == 0:
        return None
    elif output.exit_code > 1:
        raise Exception(f"Diff command execution failed. {output.stdout}\n{output.stderr}")
    else:
        return output.stderr


# Any character other than whitespaces could be used as a sed separator.
# The separator must not be used in pattern string, which is given as a sed parameter, so there is
# a short list of possible separator characters, from which the first one not occuring in patterns
# is selected
def get_sed_separator(first_pattern, second_pattern=None):
    sed_separators = ['/', ':', ';', ',', '.']
    if second_pattern is None:
        second_pattern = ''
    for char in sed_separators:
        if char in first_pattern or char in second_pattern:
            continue
        else:
            return char
    raise ValueError("Sed separator cannot be empty.")


def insert_line_before_pattern(file, pattern, new_line):
    separator = get_sed_separator(pattern)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i '{separator}{pattern}{separator}i {new_line}' {file}"
    return TestRun.executor.run_expect_success(cmd)


def replace_first_pattern_occurence(file, pattern, new_line):
    separator = get_sed_separator(pattern, new_line)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i '0,{separator}{pattern}{separator}s" \
        f"{separator}{pattern}{separator}{new_line}{separator}' {file}"
    return TestRun.executor.run_expect_success(cmd)


def replace_in_lines(file, pattern, new_line, regexp=False):
    separator = get_sed_separator(pattern, new_line)
    pattern = pattern.replace("'", "\\x27")
    new_line = new_line.replace("'", "\\x27")
    cmd = f"sed -i{' -r' if regexp else ''} " \
        f"'s{separator}{pattern}{separator}{new_line}{separator}g' {file}"
    return TestRun.executor.run_expect_success(cmd)


def read_file(file):
    if not file.strip():
        raise ValueError("File path cannot be empty or whitespace.")
    output = TestRun.executor.run_expect_success(f"cat {file}")
    return output.stdout


def write_file(file, content, overwrite: bool = True, unix_line_end: bool = True):
    if not file.strip():
        raise ValueError("File path cannot be empty or whitespace.")
    if not content:
        raise ValueError("Content cannot be empty.")
    if unix_line_end:
        content.replace('\r', '')
    content += '\n'
    max_length = 60000
    split_content = textwrap.TextWrapper(width=max_length, replace_whitespace=False).wrap(content)
    split_content[-1] += '\n'
    for s in split_content:
        redirection_char = '>' if overwrite else '>>'
        overwrite = False
        encoded_content = base64.b64encode(s.encode("utf-8"))
        cmd = f"printf '{encoded_content.decode('utf-8')}' " \
            f"| base64 --decode {redirection_char} {file}"
        TestRun.executor.run_expect_success(cmd)


def uncompress_archive(file, destination=None):
    from test_utils.filesystem.file import File

    if not isinstance(file, File):
        file = File(file)
    if not destination:
        destination = file.parent_dir
    command = (f"unzip -u {file.full_path} -d {destination}"
               if str(file).endswith(".zip")
               else f"tar --extract --file={file.full_path} --directory={destination}")
    TestRun.executor.run_expect_success(command)


def ls(path, options=''):
    default_options = "-lA --time-style=+'%Y-%m-%d %H:%M:%S'"
    output = TestRun.executor.run_expect_success(
        f"ls {default_options} {options} {path}")
    return output.stdout


def ls_item(path):
    return ls(path, '-d').splitlines()[0]


def parse_ls_output(ls_output, dir_path=''):
    split_output = ls_output.split('\n')
    fs_items = []
    for line in split_output:
        if not line.strip():
            continue
        line_fields = line.split()
        if len(line_fields) < 8:
            continue
        file_type = line[0]
        if file_type not in ['-', 'd', 'l', 'b', 'c', 'p', 's']:
            continue
        permissions = line_fields[0][1:].replace('.', '')
        owner = line_fields[2]
        group = line_fields[3]
        size = Size(float(line_fields[4]), Unit.Byte)
        split_date = line_fields[5].split('-')
        split_time = line_fields[6].split(':')
        modification_time = datetime(int(split_date[0]), int(split_date[1]), int(split_date[2]),
                                     int(split_time[0]), int(split_time[1]), int(split_time[2]))
        if dir_path and file_type != 'l':
            full_path = '/'.join([dir_path, line_fields[7]])
        else:
            full_path = line_fields[7]

        from test_utils.filesystem.file import File, FsItem
        from test_utils.filesystem.directory import Directory
        from test_utils.filesystem.symlink import Symlink

        if file_type == '-':
            fs_item = File(full_path)
        elif file_type == 'd':
            fs_item = Directory(full_path)
        elif file_type == 'l':
            target_path = TestRun.executor.run(f"readlink -f {full_path}").stdout
            fs_item = Symlink(full_path, target_path)
        else:
            fs_item = FsItem(full_path)

        fs_item.permissions.user = Permissions['|'.join(list(permissions[:3].replace('-', '')))]\
            if permissions[:3] != '---' else Permissions(0)
        fs_item.permissions.group = Permissions['|'.join(list(permissions[3:6].replace('-', '')))]\
            if permissions[3:6] != '---' else Permissions(0)
        fs_item.permissions.other = Permissions['|'.join(list(permissions[6:].replace('-', '')))]\
            if permissions[6:] != '---' else Permissions(0)

        fs_item.owner = owner
        fs_item.group = group
        fs_item.size = size
        fs_item.modification_time = modification_time
        fs_items.append(fs_item)
    return fs_items
