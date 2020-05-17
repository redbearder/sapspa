"""
Module to utilize SAP Technology components

:author: sisingh
:organization: SUSE LLC
:contact: sisingh@suse.com

:since: 2020-03-12
"""
#TODO: Add support for other SAPCAR functionalties apart from extraction

import os

from shaptools import shell


class SapUtilsError(Exception):
    """
    Error during SapUtils command execution
    """


class FileDoesNotExistError(SapUtilsError):
    """
    Error when the specified files does not exist
    """


def extract_sapcar_file(sapcar_exe, sar_file, **kwargs):
    """
    Execute SAPCAR command to decompress a SAP CAR or SAR archive files.
    If user and password are provided it will be executed with this user.

    Args:
        sapcar_exe(str): Path to the SAPCAR executable
        sar_file (str): Path to the sar file to be extracted
        options (str, opt): Additional options to SAPCAR command
        output_dir (str, opt): Directory where archive will be extracted. It creates the dir
            if the path doesn't exist. If it's not set the current dir is used
        user (str, opt): User to execute the SAPCAR command
        password (str, opt): User password
        remote_host (str, opt): Remote host where the command will be executed
    """
    if not os.path.isfile(sapcar_exe):
        raise FileDoesNotExistError('SAPCAR executable \'{}\' does not exist'.format(sapcar_exe))
    if not os.path.isfile(sar_file):
        raise FileDoesNotExistError('The SAR file \'{}\' does not exist'.format(sar_file))

    options = kwargs.get('options', None)
    output_dir = kwargs.get('output_dir', None)
    user = kwargs.get('user', None)
    password = kwargs.get('password', None)
    remote_host = kwargs.get('remote_host', None)

    output_dir_str = ' -R {}'.format(output_dir) if output_dir else ''
    options_str = ' {}'.format(options) if options else ''

    cmd = '{sapcar_exe} -xvf {sar_file}{options_str}{output_dir_str}'.format(
        sapcar_exe=sapcar_exe, sar_file=sar_file,
        options_str=options_str, output_dir_str=output_dir_str)

    result = shell.execute_cmd(cmd, user=user, password=password, remote_host=remote_host)
    if result.returncode:
        raise SapUtilsError('Error running SAPCAR command')
    return result
