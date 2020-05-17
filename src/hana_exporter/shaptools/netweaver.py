"""
SAP Netweaver management module

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2010-07-30
"""

from __future__ import print_function

import logging
import time
import fileinput
import re

from shaptools import shell

# python2 and python3 compatibility for string usage
try:
    basestring
except NameError:  # pragma: no cover
    basestring = str


class NetweaverError(Exception):
    """
    Error during Netweaver command execution
    """


class NetweaverInstance(object):
    """
    SAP Netweaver instance implementation

    Args:
        sid (str): SAP Netweaver sid
        inst (str): SAP Netweaver instance number
        password (str): Netweaver instance password
        remote_host (str, opt): Remote host where the command will be executed
    """

    # SID is usualy written uppercased, but the OS user is always created lower case.
    NETWEAVER_USER = '{sid}adm'.lower()
    UNINSTALL_PRODUCT = 'NW_Uninstall:GENERIC.IND.PD'
    GETPROCESSLIST_SUCCESS_CODES = [0, 3, 4]
    SUCCESSFULLY_INSTALLED = 0
    UNSPECIFIED_ERROR = 111

    def __init__(self, sid, inst, password, **kwargs):
        # Force instance nr always with 2 positions.
        inst = '{:0>2}'.format(inst)
        if not all(isinstance(i, basestring) for i in [sid, inst, password]):
            raise TypeError(
                'provided sid, inst and password parameters must be str type')

        self._logger = logging.getLogger('{}{}'.format(sid, inst))
        self.sid = sid
        self.inst = inst
        self._password = password
        self.remote_host = kwargs.get('remote_host', None)

    def _execute_sapcontrol(self, sapcontrol_function, **kwargs):
        """
        Execute sapcontrol commands and return result

        Args:
            sapcontrol_function (str): sapcontrol function
            exception (boolean): Raise NetweaverError non-zero return code (default true)
            host (str, optional): Host where the command will be executed
            inst (str, optional): Use a different instance number
            user (str, optional): Define a different user for the command
            password (str, optional): The new user password

        Returns:
            ProcessResult: ProcessResult instance storing subprocess returncode,
                stdout and stderr
        """
        exception = kwargs.get('exception', True)
        # The -host and -user parameters are used in sapcontrol to authorize commands execution
        # in remote host Netweaver instances
        host = kwargs.get('host', None)
        inst = kwargs.get('inst', self.inst)
        user = kwargs.get('user', None)
        password = kwargs.get('password', None)
        if user and not password:
            raise NetweaverError('Password must be provided together with user')

        host_str = '-host {} '.format(host) if host else ''
        user_str = '-user {} {} '.format(user, password) if user else ''

        user = self.NETWEAVER_USER.format(sid=self.sid)
        cmd = 'sapcontrol {host}{user}-nr {instance} -function {sapcontrol_function}'.format(
            host=host_str, user=user_str, instance=inst, sapcontrol_function=sapcontrol_function)

        result = shell.execute_cmd(cmd, user, self._password, self.remote_host)

        if exception and result.returncode != 0:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))

        return result

    @staticmethod
    def get_attribute_from_file(conf_file, attribute_pattern):
        """
        Get attribute from file using a pattern
        """
        with open(conf_file, 'r') as file_content:
            attribute_data = shell.find_pattern(attribute_pattern, file_content.read())
        return attribute_data

    @staticmethod
    def _is_ascs_installed(processes):
        """
        Check if ASCS instance is installed
        """
        msg_server = shell.find_pattern(r'msg_server, MessageServer,.*', processes.output)
        enserver = shell.find_pattern(r'enserver, EnqueueServer,.*', processes.output)
        return bool(msg_server and enserver)

    @staticmethod
    def _is_ers_installed(processes):
        """
        Check if ERS instance is installed
        """
        enrepserver = shell.find_pattern(r'enrepserver, EnqueueReplicator,.*', processes.output)
        return bool(enrepserver)

    @staticmethod
    def _is_app_server_installed(processes):
        """
        Check if an application server (PAS or AAS) instance is installed
        """
        disp = shell.find_pattern(r'disp\+work, Dispatcher,.*', processes.output)
        igswd = shell.find_pattern(r'igswd_mt, IGS Watchdog,.*', processes.output)
        gwrd = shell.find_pattern(r'gwrd, Gateway,.*', processes.output)
        icman = shell.find_pattern(r'icman, ICM,.*', processes.output)
        return bool(disp and igswd and gwrd and icman)

    def is_installed(self, sap_instance=None):
        """
        Check if SAP Netweaver is installed

        Args:
            sap_instance (str): SAP instance type. Available options: ascs, ers, ci, di
                If None, if any NW installation is existing will be checked

        Returns:
            bool: True if SAP instance is installed, False otherwise
        """
        processes = self.get_process_list(False)
        # TODO: Might be done using a dictionary to store the methods and keys
        if processes.returncode not in self.GETPROCESSLIST_SUCCESS_CODES:
            state = False
        elif not sap_instance:
            state = True
        elif sap_instance == 'ascs':
            state = self._is_ascs_installed(processes)
        elif sap_instance == 'ers':
            state = self._is_ers_installed(processes)
        elif sap_instance in ['ci', 'di']:
            state = self._is_app_server_installed(processes)
        else:
            raise ValueError('provided sap instance type is not valid: {}'.format(sap_instance))
        return state

    @staticmethod
    def _remove_old_files(cwd, root_user, password, remote_host):
        """
        Remove old files from SAP installation cwd folder. Only start_dir.cd must remain
        """
        # TODO: check start_dir.cd exists
        remove_files_cmd = "printf '%q ' {}/*".format(cwd)
        remove_files = shell.execute_cmd(
            remove_files_cmd, root_user, password, remote_host)
        remove_files = remove_files.output.replace('{}/start_dir.cd'.format(cwd), '')
        cmd = 'rm -rf {}'.format(remove_files)
        shell.execute_cmd(cmd, root_user, password, remote_host)

    @classmethod
    def update_conf_file(cls, conf_file, **kwargs):
        """
        Update NW installation config file parameters. Add the parameters if they don't exist

        Args:
            conf_file (str): Path to the netweaver installation configuration file
            kwargs (opt): Dictionary with the values to be updated.
                Use the exact name of the netweaver configuration file

        kwargs can be used in the next two modes:
            update_conf_file(conf_file, sid='HA1', hostname='hacert01')
            update_conf_file(conf_file, **{'sid': 'HA1', 'hostname': 'hacert01'})
        """
        for key, value in kwargs.items():
            pattern = '{key}\s+=.*'.format(key=key)
            new_value = '{key} = {value}'.format(key=key, value=value)
            with open(conf_file, 'r+') as file_cache:
                if key in file_cache.read():
                    for line in fileinput.input(conf_file, inplace=1):
                        line = re.sub(pattern, new_value, line)
                        print(line, end='')
                else:
                    file_cache.write('\n'+new_value)
        return conf_file

    @classmethod
    def install(
            cls, software_path, virtual_host, product_id, conf_file, root_user, password, **kwargs):
        """
        Install SAP Netweaver instance

        Args:
            software_path (str): Path where SAP Netweaver 'sapinst' tool is located
            virtual_host (str): Virtual host name of the machine
            product_id (str): SAP instance product id
            conf_file (str): Path to the configuration file
            root_user (str): Root user name
            password (str): Root user password
            cwd (str, opt): New value for SAPINST_CWD parameter
                CAUTION: All of the files stored in this path will be removed except the
                start_dir.cd. This folder only will contain temporary files about the installation.
            exception (bool, opt): Raise and exception in case of error if True, return result
                object otherwise
            remote_host (str, opt): Remote host where the command will be executed
        """
        cwd = kwargs.get('cwd', None)
        raise_exception = kwargs.get('exception', True)
        remote_host = kwargs.get('remote_host', None)

        if cwd:
            # This operation must be done in order to avoid incorrect files usage
            cls._remove_old_files(cwd, root_user, password, remote_host)

        cmd = '{software_path}/sapinst SAPINST_USE_HOSTNAME={virtual_host} '\
            'SAPINST_EXECUTE_PRODUCT_ID={product_id} '\
            'SAPINST_SKIP_SUCCESSFULLY_FINISHED_DIALOG=true SAPINST_START_GUISERVER=false '\
            'SAPINST_INPUT_PARAMETERS_URL={conf_file}{cwd}'.format(
                software_path=software_path,
                virtual_host=virtual_host,
                product_id=product_id,
                conf_file=conf_file,
                cwd=' SAPINST_CWD={}'.format(cwd) if cwd else '')
        result = shell.execute_cmd(cmd, root_user, password, remote_host)
        if result.returncode and raise_exception:
            raise NetweaverError('SAP Netweaver installation failed')
        return result

    @classmethod
    def _ascs_restart_needed(cls, installation_result):
        """
        Check the ERS installation return code and output to see if the ASCS instance restart
        is needed

        Args:
            installation_result (shell.ProcessResult): ERS installation result

        Returns: True if ASCS restart is needed, False otherwise
        """
        expected_msg = \
            '<html><p>Error when stopping instance.</p><p>Cannot stop instance <i>(.*)'\
            '</i> on host <i>(.*)</i>.</p><p>Stop the instance manually and choose <i>OK</i> to '\
            'continue.</html>'
        if installation_result.returncode == cls.UNSPECIFIED_ERROR:
            if shell.find_pattern(expected_msg, installation_result.output):
                return True
        return False

    @classmethod
    def _restart_ascs(cls, conf_file, ers_pass, ascs_pass, remote_host=None):
        """
        Restart ascs from the ERS host.

        Args:
            conf_file (str): Path to the configuration file
            ascs_pass (str): ASCS instance password
            remote_host (str, optional): Remote host where the command will be executed
        """
        # Get sid and instance number from configuration file
        sid = cls.get_attribute_from_file(
            conf_file, 'NW_readProfileDir.profileDir += +.*/(.*)/profile').group(1).lower()
        instance_number = cls.get_attribute_from_file(
            conf_file, 'nw_instance_ers.ersInstanceNumber += +(.*)').group(1)
        ers = cls(sid, instance_number, ers_pass, remote_host=remote_host)
        result = ers.get_system_instances(exception=False)
        ascs_data = shell.find_pattern(
            '(.*), (.*), (.*), (.*), (.*), MESSAGESERVER|ENQUE, GREEN', result.output)

        ascs_user = '{}adm'.format(sid).lower()
        ascs_hostname = ascs_data.group(1)
        ascs_instance_number = ascs_data.group(2)

        ers.stop(host=ascs_hostname, inst=ascs_instance_number, user=ascs_user, password=ascs_pass)
        ers.start(host=ascs_hostname, inst=ascs_instance_number, user=ascs_user, password=ascs_pass)

    @classmethod
    def install_ers(
            cls, software_path, virtual_host, product_id, conf_file, root_user, password, **kwargs):
        """
        Install SAP Netweaver ERS instance. ERS instance installation needs an active polling
        the instance where the ASCS is installed.

        Args:
            software_path (str): Path where SAP Netweaver 'sapinst' tool is located
            virtual_host (str): Virtual host name of the machine
            product_id (str): SAP instance product id
            conf_file (str): Path to the configuration file
            root_user (str): Root user name
            password (str): Root user password
            ascs_password (str, optional): Password of the SAP user in the machine hosting the
                ASCS instance. If it's not set the same password used to install ERS will be used
            timeout (int, optional): Timeout of the installation process. If 0 it will try to
                install the instance only once
            interval (int, optional): Retry interval in seconds
            remote_host (str, opt): Remote host where the command will be executed
        """
        timeout = kwargs.get('timeout', 0)
        interval = kwargs.get('interval', 5)
        ers_pass = cls.get_attribute_from_file(
            conf_file, 'nwUsers.sidadmPassword += +(.*)').group(1)
        ascs_pass = kwargs.get('ascs_password', ers_pass)
        remote_host = kwargs.get('remote_host', None)
        cwd = kwargs.get('cwd', None)

        current_time = time.time()
        current_timeout = current_time + timeout
        while current_time <= current_timeout:
            result = cls.install(
                software_path, virtual_host, product_id, conf_file, root_user, password,
                exception=False, remote_host=remote_host, cwd=cwd)

            if result.returncode == cls.SUCCESSFULLY_INSTALLED:
                break
            elif cls._ascs_restart_needed(result):
                cls._restart_ascs(conf_file, ers_pass, ascs_pass, remote_host)
                break

            time.sleep(interval)
            current_time = time.time()
        else:
            raise NetweaverError(
                'SAP Netweaver ERS installation failed after {} seconds'.format(timeout))

    def uninstall(self, software_path, virtual_host, conf_file, root_user, password, **kwargs):
        """
        Uninstall SAP Netweaver instance

        Args:
            software_path (str): Path where SAP Netweaver 'sapinst' tool is located
            virtual_host (str): Virtual host name of the machine
            conf_file (str): Path to the configuration file
            root_user (str): Root user name
            password (str): Root user password
            remote_host (str, opt): Remote host where the command will be executed
        """
        remote_host = kwargs.get('remote_host', None)
        user = self.NETWEAVER_USER.format(sid=self.sid)
        self.install(
            software_path, virtual_host, self.UNINSTALL_PRODUCT, conf_file, root_user, password,
            remote_host=remote_host)
        shell.remove_user(user, True, root_user, password, remote_host)

    def get_process_list(self, exception=True, **kwargs):
        """
        Get SAP processes list
        """
        result = self._execute_sapcontrol('GetProcessList', exception=False, **kwargs)
        if exception and result.returncode not in self.GETPROCESSLIST_SUCCESS_CODES:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))
        return result

    def get_system_instances(self, exception=True, **kwargs):
        """
        Get SAP system instances list
        """
        result = self._execute_sapcontrol('GetSystemInstanceList', exception=False, **kwargs)
        if exception and result.returncode:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))
        return result

    def get_instance_properties(self, exception=True, **kwargs):
        """
        Get SAP instance properties
        """
        result = self._execute_sapcontrol('GetInstanceProperties', exception=False, **kwargs)
        if exception and result.returncode:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))
        return result

    def start(self, wait=15, delay=0, exception=True, **kwargs):
        """
        Start SAP instance
        Args:
            wait (int): Time to wait until the processes are started in seconds
        """
        if wait:
            cmd = 'StartWait {} {}'.format(wait, delay)
        else:
            cmd = 'Start'
        result = self._execute_sapcontrol(cmd, exception=False, **kwargs)
        if exception and result.returncode:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))
        return result

    def stop(self, wait=15, delay=0, exception=True, **kwargs):
        """
        Stop SAP instance
        Args:
            wait (int): Time to wait until the processes are stopped in seconds
        """
        if wait:
            cmd = 'StopWait {} {}'.format(wait, delay)
        else:
            cmd = 'Stop'
        result = self._execute_sapcontrol(cmd, exception=False, **kwargs)
        if exception and result.returncode:
            raise NetweaverError('Error running sapcontrol command: {}'.format(result.cmd))
        return result
