"""
Module to interact with the shell commands.

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2018-11-15
"""

import logging
import os
import subprocess
import shlex
import re

LOGGER = logging.getLogger('shell')
ASKPASS_SCRIPT = 'support/ssh_askpass'


class ShellError(Exception):
    """
    Exceptions in shell module
    """


class ProcessResult:
    """
    Class to store subprocess.Popen output information and offer some
    functionalities

    Args:
        cmd (str): Executed command
        returncode (int): Subprocess return code
        output (str): Subprocess output string
        err (str): Subprocess error string
    """

    def __init__(self, cmd, returncode, output, err):
        self.cmd = cmd
        self.returncode = returncode
        self.output = output.decode() # Make it compatiable with python2 and 3
        self.err = err.decode()


def log_command_results(stdout, stderr):
    """
    Log process stdout and stderr text
    """
    logger = logging.getLogger(__name__)
    if stdout:
        for line in stdout.splitlines():
            logger.info(line)
    if stderr:
        for line in stderr.splitlines():
            logger.error(line)


def find_pattern(pattern, text):
    """
    Find pattern in multiline string

    Args:
        pattern (str): Regular expression pattern
        text (str): string to search in

    Returns:
        Match object if the pattern is found, None otherwise
    """
    for line in text.splitlines():
        found = re.match(pattern, line)
        if found:
            return found
    return None


def format_su_cmd(cmd, user):
    """
    Format the command to be executed by other user using su option

    Args:
        cmd (str): Command to be formatted
        user (str): User to executed the command

    Returns:
        str: Formatted command
    """
    return 'su -lc "{cmd}" {user}'.format(cmd=cmd, user=user)


def format_remote_cmd(cmd, remote_host, user):
    """
    Format cmd to run remotely using ssh

    Args:
        cmd (str): Command to be executed
        remote_host (str): User password
        user (str): User to execute the command

    Returns:
        str: cmd adapted to be executed remotely
    """
    if not user:
        raise ValueError('user must be provided')

    cmd = 'ssh {user}@{remote_host} "bash --login -c \'{cmd}\'"'.format(
        user=user, remote_host=remote_host, cmd=cmd)
    return cmd


def create_ssh_askpass(password, cmd):
    """
    Create ask pass command
    Note: subprocess os.setsid doesn't work as the user might have a password

    Args:
        password (str): ssh command password
        cmd (str): Command to run
    """
    dirname = os.path.dirname(__file__)
    ask_pass_script = os.path.join(dirname, ASKPASS_SCRIPT)
    ssh_askpass_str = 'export SSH_ASKPASS={};export PASS={};export DISPLAY=:0;setsid {}'.format(
        ask_pass_script, password, cmd)
    return ssh_askpass_str


def execute_cmd(cmd, user=None, password=None, remote_host=None):
    """
    Execute a shell command. If user and password are provided it will be
    executed with this user.

    Args:
        cmd (str): Command to be executed
        user (str, opt): User to execute the command
        password (str, opt): User password
        remote_host (str, opt): Remote host where the command will be executed

    Returns:
        ProcessResult: ProcessResult instance storing subprocess returncode,
            stdout and stderr
    """

    LOGGER.debug('Executing command "%s" with user %s', cmd, user)

    if remote_host:
        cmd = format_remote_cmd(cmd, remote_host, user)
        LOGGER.debug('Command updated to "%s"', cmd)

    elif user:
        cmd = format_su_cmd(cmd, user)
        LOGGER.debug('Command updated to "%s"', cmd)

    proc = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Make it compatiable with python2 and 3
    if password:
        password = password.encode()
    out, err = proc.communicate(input=password)

    result = ProcessResult(cmd, proc.returncode, out, err)
    log_command_results(out, err)

    return result

def remove_user(user, force=False, root_user=None, root_password=None, remote_host=None):
    """
    Remove user from system
    Args:
        user (str): User to remove
        force (bool): Force the remove process even though the user is used in some process
        remote_host (str, opt): Remote host where the command will be executed
    """
    cmd = 'userdel {}'.format(user)
    process_executing = r'userdel: user {} is currently used by process (.*)'.format(user)
    while True:
        result = execute_cmd(cmd, root_user, root_password, remote_host)
        if result.returncode == 0:
            return
        elif force:
            process_pid = find_pattern(process_executing, result.err)
            if not process_pid:
                break
            kill_cmd = 'kill -9 {}'.format(process_pid.group(1))
            execute_cmd(kill_cmd, root_user, root_password, remote_host)
        else:
            break
    raise ShellError('error removing user {}'.format(user))
