"""
SAP HANA management module

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2018-11-15
"""
#TODO: Modify code to work when multiple HANA instances are installed
#TODO: Check backup already exist method
#TODO: Copy ssfs files method? Add hostname? Or do this using salt
#TODO: Split commands by version. Create backup for example

from __future__ import print_function

import logging
import fileinput
import re
import time
import platform
import os

from shaptools import shell

# python2 and python3 compatibility for string usage
try:
    basestring
except NameError:  # pragma: no cover
    basestring = str


class HanaError(Exception):
    """
    Error during HANA command execution
    """

class FileDoesNotExistError(HanaError):
    """
    Error when the specified files does not exist
    """

class HanaSoftwareNotFoundError(HanaError):
    """
    HANA installation software not found
    """

# System replication states
# Random value used
SR_STATES = {
    0: 'DISABLED',
    1: 'PRIMARY',
    2: 'SECONDARY'
}


# System replication statuses.
# Value get from HDBSettings.sh systemReplicationStatus.py return code
SR_STATUS = {
    10: 'NONE',
    11: 'ERROR',
    12: 'UNKNOWN',
    13: 'INITIALIZING',
    14: 'SYNCING',
    15: 'ACTIVE'
}


class HanaInstance(object):
    """
    SAP HANA instance implementation

    Args:
        sid (str): SAP HANA sid to enable
        inst (str): SAP HANA instance number
        password (str): HANA instance password
        remote_host (str, opt): Remote host where the command will be executed
    """

    PATH = '/usr/sap/{sid}/HDB{inst}/'
    INSTALL_EXEC = 'hdblcm'
    HANA_PLATFORM = '^HDB:HANA:.*:{platform}:.*'
    SUPPORTED_PLATFORMS = [
        'x86_64', 'ppc64le'
    ]
    SUPPORTED_SYSTEMS = ['Linux']
    # SID is usualy written uppercased, but the OS user is always created lower case.
    HANAUSER = '{sid}adm'.lower()
    SYNCMODES = ['sync', 'syncmem', 'async']
    SUCCESSFULLY_REGISTERED = 0 # Node correctly registered as secondary node
    SSFS_DIFFERENT_ERROR = 149 # ssfs files are different in the two nodes error return code

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

    @classmethod
    def get_platform(cls):
        """
        Get the SAP HANA installation folder by platform
        """
        current_platform = platform.machine()
        logger = logging.getLogger('__name__')
        logger.info('current platform is %s', current_platform)
        if current_platform not in cls.SUPPORTED_PLATFORMS:
            raise ValueError('not supported platform: {}'.format(current_platform))

        current_system = platform.system()
        logger.info('current system is %s', current_system)
        if current_system not in cls.SUPPORTED_SYSTEMS:
            raise ValueError('not supported system: {}'.format(current_system))

        return '{}_{}'.format(current_system.upper(), current_platform.upper())

    @classmethod
    def find_hana_hdblcm(cls, software_path):
        """
        Find a HANA installation executable in a folder (and subfolders)

        Args:
            software_path (str): Path of a folder where the HANA installation software is
            available
        """
        logger = logging.getLogger('__name__')
        # hdbclm in the provider folder
        hdblcm_path = os.path.join(software_path, cls.INSTALL_EXEC)
        if os.path.exists(hdblcm_path):
            logger.info('HANA installer found: %s', hdblcm_path)
            return hdblcm_path

        # HANA platform folder
        label_file = os.path.join(software_path, 'LABEL.ASC')
        if os.path.exists(label_file):
            with open(label_file) as file_ptr:
                hana_platform = cls.get_platform()
                hana_pattern = cls.HANA_PLATFORM.format(platform=hana_platform)
                if re.match(hana_pattern, file_ptr.read()):
                    hdblcm_path = os.path.join(
                        software_path, 'DATA_UNITS',
                        'HDB_LCM_{}'.format(hana_platform), cls.INSTALL_EXEC)
                    hdbserver_path = os.path.join(
                        software_path, 'DATA_UNITS',
                        'HDB_SERVER_{}'.format(hana_platform), cls.INSTALL_EXEC)
                    if os.path.exists(hdblcm_path):
                        logger.info('HANA installer found: %s', hdblcm_path)
                        return hdblcm_path
                    elif os.path.exists(hdbserver_path):
                        logger.info('HANA installer found: %s', hdbserver_path)
                        return hdbserver_path

        # HANA server SAR patch
        hana_server_path = os.path.join(software_path, 'SAP_HANA_DATABASE', cls.INSTALL_EXEC)
        if os.path.exists(hana_server_path):
            logger.info('HANA installer found: %s', hana_server_path)
            return hana_server_path

        raise HanaSoftwareNotFoundError('HANA installer not found in {}'.format(software_path))

    def _run_hana_command(self, cmd, exception=True):
        """
        Run hana command

        Args:
            cmd (str): HANA command
            exception (boolean): Raise HanaError non-zero return code (default true)

        Returns:
            ProcessResult: ProcessResult instance storing subprocess returncode,
                stdout and stderr
        """
        #TODO: Add absolute paths to hana commands using sid and inst number
        user = self.HANAUSER.format(sid=self.sid)
        result = shell.execute_cmd(cmd, user, self._password, self.remote_host)

        if exception and result.returncode != 0:
            raise HanaError('Error running hana command: {}'.format(result.cmd))

        return result

    def is_installed(self):
        """
        Check if SAP HANA is installed

        Returns:
            bool: True if installed, False otherwise
        """
        user = self.HANAUSER.format(sid=self.sid)
        try:
            result = shell.execute_cmd('HDB info', user, self._password, self.remote_host)
            return not result.returncode
        except EnvironmentError as err: #FileNotFoundError is not compatible with python2
            self._logger.error(err)
            return False

    @classmethod
    def update_conf_file(cls, conf_file, **kwargs):
        """
        Update config file parameters

        Args:
            conf_file (str): Path to the configuration file
            kwargs (opt): Dictionary with the values to be updated.
                Use the exact name of the SAP configuration file for the key

        kwargs can be used in the next two modes:
            update_conf_file(conf_file, sid='PRD', hostname='hana01')
            update_conf_file(conf_file, **{'sid': 'PRD', 'hostname': 'hana01'})
        """
        for key, value in kwargs.items():
            pattern = '^{key}=.*'.format(key=key)
            new_value = '{key}={value}'.format(key=key, value=value)
            for line in fileinput.input(conf_file, inplace=1):
                line = re.sub(pattern, new_value, line)
                print(line, end='')
        return conf_file

    @classmethod
    def update_hdb_pwd_file(cls, hdb_pwd_file, **kwargs):
        """
        Update SAP HANA XML passwords

        Args:
            hdb_pwd_file (str): Path to the XML passwords file
            kwargs (opt): Dictionary with the values to be updated.
                Use the exact name of the XML file for the key

        kwargs can be used in the next two modes:
            update_hdb_pwd_file(hdb_pwd_file, master_password='Test123', sapadm_password='pas11')
            update_hdb_pwd_file(hdb_pwd_file, **{'master_password': 'Test123', 'sapadm_password': 'pas11'})
        """
        for key, value in kwargs.items():
            pattern = '<{key}>.*'.format(key=key)
            new_entry = '<{key}><![CDATA[{value}]]></{key}>'.format(key=key, value=value)
            for line in fileinput.input(hdb_pwd_file, inplace=1):
                line = re.sub(pattern, new_entry, line)
                print(line, end='')
        return hdb_pwd_file

    @classmethod
    def create_conf_file(
            cls, software_path, conf_file, root_user, root_password, remote_host=None):
        """
        Create SAP HANA configuration file

        Args:
            software_path (str): Path where SAP HANA software is downloaded
            conf_file (str): Path where configuration file will be created
            root_user (str): Root user name
            root_password (str): Root user password
            remote_host (str, opt): Remote host where the command will be executed

        """
        executable = cls.find_hana_hdblcm(software_path)
        cmd = '{executable} --action=install '\
            '--dump_configfile_template={conf_file}'.format(
                executable=executable, conf_file=conf_file)
        result = shell.execute_cmd(cmd, root_user, root_password, remote_host)
        if result.returncode:
            raise HanaError('SAP HANA configuration file creation failed')
        return conf_file

    @classmethod
    def install(
            cls, software_path, conf_file, root_user, password,
            hdb_pwd_file=None, remote_host=None):
        """
        Install SAP HANA platform providing a configuration file

        Args:
            software_path (str): Path where SAP HANA software is downloaded
            conf_file (str): Path to the configuration file
            root_user (str): Root user name
            password (str): Root user password
            hdb_pwd_file (str, opt): Path to the XML password file
            remote_host (str, opt): Remote host where the command will be executed
        """
        # TODO: mount partition if needed
        # TODO: do some integrity check stuff

        if not os.path.isfile(conf_file):
            raise FileDoesNotExistError(
                'The configuration file \'{}\' does not exist'.format(conf_file))
        if hdb_pwd_file is not None and not os.path.isfile(hdb_pwd_file):
            raise FileDoesNotExistError(
                'The XML password file \'{}\' does not exist'.format(hdb_pwd_file))
        executable = cls.find_hana_hdblcm(software_path)
        if hdb_pwd_file:
            cmd = 'cat {hdb_pwd_file} | {executable} -b '\
                '--read_password_from_stdin=xml --configfile={conf_file}'.format(
                    hdb_pwd_file=hdb_pwd_file, executable=executable, conf_file=conf_file)
        else:
            cmd = '{executable} -b --configfile={conf_file}'.format(
                executable=executable, conf_file=conf_file)
        result = shell.execute_cmd(cmd, root_user, password, remote_host)
        if result.returncode:
            raise HanaError('SAP HANA installation failed')

    def uninstall(self, root_user, password, installation_folder='/hana/shared'):
        """
        Uninstall SAP HANA platform
        """
        cmd = '{installation_folder}/{sid}/hdblcm/hdblcm '\
            '--uninstall -b'.format(
                installation_folder=installation_folder, sid=self.sid.upper())
        result = shell.execute_cmd(cmd, root_user, password, self.remote_host)
        if result.returncode:
            raise HanaError('SAP HANA uninstallation failed')

    def is_running(self):
        """
        Check if SAP HANA daemon is running

        Returns:
            bool: True if running, False otherwise
        """
        cmd = 'pidof hdb.sap{sid}_HDB{inst}'.format(
            sid=self.sid.upper(), inst=self.inst)
        result = self._run_hana_command(cmd, exception=False)
        return not result.returncode

    # pylint:disable=W1401
    def get_version(self):
        """
        Get SAP HANA version
        """
        cmd = 'HDB version'
        result = self._run_hana_command(cmd)
        version_pattern = shell.find_pattern(
            r'\s+version:\s+(\d+.\d+.\d+).*', result.output)
        if version_pattern is None:
            raise HanaError('Version pattern not found in command output')
        return version_pattern.group(1)

    def start(self):
        """
        Start hana instance
        """
        cmd = 'HDB start'
        self._run_hana_command(cmd)

    def stop(self):
        """
        Stop hana instance
        """
        cmd = 'HDB stop'
        self._run_hana_command(cmd)

    def get_sr_state(self):
        """
        Get system replication state for the current node.

        Note:
        The command reads the state from the configuration files
        and so the reported state may not match the actual state.

        Returns:
            str: String between PRIMARY, SECONDARY and DISABLED

        INFO: In previous versions this was done using an enum. enum usage
        was removed to avoid dependencies
        """
        cmd = 'hdbnsutil -sr_state'
        result = self._run_hana_command(cmd)

        if shell.find_pattern('.*mode: primary.*', result.output) is not None:
            return 'PRIMARY'
        if shell.find_pattern('.*mode: ({})'.format('|'.join(self.SYNCMODES)),
                              result.output) is not None:
            return 'SECONDARY'
        return 'DISABLED'

    def get_sr_state_details(self):
        """
        Get system replication state details for the current node.
        See also get_sr_status which can provide additional details
        by parsing the output of the SAP python script
        systemReplicationStatus.py.

        Note:
        The command reads the state from the configuration files
        and so the reported state may not match the actual state.

        Returns:
            dict containing details about replication state.
        """
        cmd = 'hdbnsutil -sr_state'
        result = self._run_hana_command(cmd)
        state = {}
        for line in result.output.splitlines():
            if "Site Mappings:" in line or "Host Mappings:" in line:
                break
            data = re.match(r'^\s*([^:]+):\s+(.*)$', line.strip())
            if data is not None:
                state[data.group(1)] = data.group(2)
        return state

    def sr_enable_primary(self, name):
        """
        Enable SAP HANA system replication as primary node

        Args:
            name (str): Name to give to the node
        """
        cmd = 'hdbnsutil -sr_enable --name={}'.format(name)
        self._run_hana_command(cmd)

    def sr_disable_primary(self):
        """
        Disable SAP HANA system replication as primary node
        """
        cmd = 'hdbnsutil -sr_disable'
        self._run_hana_command(cmd)

    def copy_ssfs_files(self, remote_host, primary_pass):
        """
        Copy the ssfs data and key files to the secondary node

        Args:
            primary_pass: Password of the primary node
        """
        user = self.HANAUSER.format(sid=self.sid)
        sid_upper = self.sid.upper()
        cmd = \
            "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "\
            "{user}@{remote_host}:/usr/sap/{sid}/SYS/global/security/rsecssfs/data/SSFS_{sid}.DAT "\
            "/usr/sap/{sid}/SYS/global/security/rsecssfs/data/SSFS_{sid}.DAT".format(
                user=user, remote_host=remote_host, sid=sid_upper)
        cmd = shell.create_ssh_askpass(primary_pass, cmd)
        self._run_hana_command(cmd)

        cmd = \
            "scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "\
            "{user}@{remote_host}:/usr/sap/{sid}/SYS/global/security/rsecssfs/key/SSFS_{sid}.KEY "\
            "/usr/sap/{sid}/SYS/global/security/rsecssfs/key/SSFS_{sid}.KEY".format(
                user=user, remote_host=remote_host, sid=sid_upper)
        cmd = shell.create_ssh_askpass(primary_pass, cmd)
        self._run_hana_command(cmd)

    def sr_register_secondary(
            self, name, remote_host, remote_instance,
            replication_mode, operation_mode, **kwargs):
        """
        Register SAP HANA system replication as secondary node

        Args:
            name (str): Name to give to the node
            remote_host (str): Primary node hostname
            remote_instance (str): Primary node instance
            replication_mode (str): Replication mode
            operation_mode (str): Operation mode
            primary_password (str, optional): Password from node where system
                replicationis is enabled. Current node password will be used by
                default (xxxadm sap user password)
            timeout (int, optional): Timeout to try to register the node in seconds
            interval (int, optional): Retry interval in seconds

        """
        timeout = kwargs.get('timeout', 0)
        interval = kwargs.get('interval', 5)
        primary_pass = kwargs.get('primary_password', self._password)

        remote_instance = '{:0>2}'.format(remote_instance)
        cmd = 'hdbnsutil -sr_register --name={} --remoteHost={} '\
              '--remoteInstance={} --replicationMode={} --operationMode={}'.format(
                  name, remote_host, remote_instance, replication_mode, operation_mode)

        current_time = time.time()
        current_timeout = current_time + timeout
        while current_time <= current_timeout:
            return_code = self._run_hana_command(cmd, False).returncode
            if return_code == self.SUCCESSFULLY_REGISTERED:
                break
            elif return_code == self.SSFS_DIFFERENT_ERROR:
                self.copy_ssfs_files(remote_host, primary_pass)
                self._run_hana_command(cmd)
                break
            time.sleep(interval)
            current_time = time.time()
            continue
        else:
            raise HanaError(
                'System replication registration process failed after {} seconds'.format(
                    timeout))

    def sr_unregister_secondary(self, primary_name):
        """
        Unegister SAP HANA system replication from primary node

        Args:
            name (str): Name to give to the node
        """
        cmd = 'hdbnsutil -sr_unregister --name={}'.format(primary_name)
        self._run_hana_command(cmd)

    def sr_changemode_secondary(self, new_mode):
        """
        Change secondary mode replication mode

        Args:
            new_mode (str): New mode between sync|syncmem|async
        """
        cmd = 'hdbnsutil -sr_changemode --mode={}'.format(new_mode)
        self._run_hana_command(cmd)


    def check_user_key(self, key_name):
        """
        Check the use key existance

        Args:
            key (str): Key name

        Returns: True if it exists, False otherwise
        """
        cmd = 'hdbuserstore list {}'.format(key_name)
        try:
            self._run_hana_command(cmd)
            return True
        except HanaError:
            return False

    def create_user_key(
            self, key_name, environment, user_name, user_password, database=None):
        """
        Create or update user key entry for the database
        Args:
            key_name (str): Key name
            environment (str): Database location (host:port)
            user_name (srt): User name
            user_password (str): User password
            database (str, opt): Database name in MDC environment
        """
        database = '@{}'.format(database) if database else None
        cmd = 'hdbuserstore set {key} {env}{db} {user} {passwd}'.format(
            key=key_name, env=environment, db=database,
            user=user_name, passwd=user_password)
        self._run_hana_command(cmd)

    def _hdbsql_connect(self, **kwargs):
        """
        Create hdbsql connection string

        Args:
            key_name (str, optional): Keystore to connect to sap hana db
            user_name (str, optional): User to connect to sap hana db
            user_password (str, optional): Password to connect to sap hana db
        """
        if kwargs.get('key_name', None):
            cmd = 'hdbsql -i {} -U {}'.format(self.inst, kwargs['key_name'])
        elif kwargs.get('user_name', None) and kwargs.get('user_password', None):
            cmd = 'hdbsql -i {} -u {} -p {}'.format(
                self.inst, kwargs['user_name'], kwargs['user_password'])
        else:
            raise ValueError(
                'key_name or user_name/user_password parameters must be used')
        return cmd

    def create_backup(
            self, database, backup_name,
            key_name=None, user_name=None, user_password=None):
        """
        Create the primary node backup. key_name or user_name/user_password
        combination, one of them must be provided

        Args:
            database (str): Database name
            backup_name (str): Backup name
            key_name (str): Key name
            user_name (str): User
            user_password (str): User password
        """
        #TODO: Version check

        hdbsql_cmd = self._hdbsql_connect(
            key_name=key_name, user_name=user_name, user_password=user_password)

        cmd = '{} -d {} '\
              '\\"BACKUP DATA FOR FULL SYSTEM USING FILE (\'{}\')\\"'.format(
                  hdbsql_cmd, database, backup_name)
        self._run_hana_command(cmd)

    def sr_cleanup(self, force=False):
        """
        Clean system replication state

        Args:
            force (bool): Force cleanup
        """
        cmd = 'hdbnsutil -sr_cleanup{}'.format(' --force' if force else '')
        self._run_hana_command(cmd)

    def _parse_replication_output(self, output):
        """
        Utility function to parse output of
        systemReplicationStatus.py
        TODO: Parse table data
        TODO: Parse local state
        """
        return {}

    def get_sr_status(self):
        """
        Get system replication status (parsed output
        of systemReplicationStatus.py).

        Returns:
            str: Strings from SR_STATUS dictionary (UNKNOWN if the return code
            is not defined)
        """
        cmd = 'HDBSettings.sh systemReplicationStatus.py'
        result = self._run_hana_command(cmd, exception=False)
        status = self._parse_replication_output(result.output)
        # TODO: Handle HANA bug where non-working SR resulted in RC 15
        # (see SAPHana RA)
        status["status"] = SR_STATUS.get(result.returncode, SR_STATUS[12])
        return status

    def _manage_ini_file(
            self, parameter_str, database, file_name, layer,
            **kwargs):
        """
        Construct command with HANA SQL to update configuration parameters in ini file

        key_name or user_name/user_password parameters must be used
        Args:
            parameter_str (list): List containing HANA parameter details in a dict format
            database (str): Database name
            file_name (str): INI configuration file name
            layer (str): Target layer for the configuration change 'SYSTEM', 'HOST' or 'DATABASE'
            layer_name (str, optional): Target either a tenant name or a target host name
            reconfig (bool, optional): If apply changes to running HANA instance
            set_value (bool, optional): Choose SET or UNSET operation to update parameters
            key_name (str, optional): Keystore to connect to sap hana db
            user_name (str, optional): User to connect to sap hana db
            user_password (str, optional): Password to connect to sap hana db
        """
        layer_name = kwargs.get('layer_name', None)
        reconfig = kwargs.get('reconfig', False)
        set_value = kwargs.get('set_value', True)
        key_name = kwargs.get('key_name', None)
        user_name = kwargs.get('user_name', None)
        user_password = kwargs.get('user_password', None)

        hdbsql_cmd = self._hdbsql_connect(
            key_name=key_name, user_name=user_name, user_password=user_password)

        if layer in ('HOST', 'DATABASE') and layer_name is not None:
            layer_name_str = ', \'{}\''.format(layer_name)
        else:
            layer_name_str = ''

        set_str = 'SET' if set_value else 'UNSET'
        reconfig_option = ' WITH RECONFIGURE' if reconfig else ''

        cmd = ('{hdbsql_cmd} -d {db} '
               '\\"ALTER SYSTEM ALTER CONFIGURATION(\'{file_name}\', \'{layer}\'{layer_name}) '
               '{set_str}{parameter_str}{reconfig};\\"'.format(
                   hdbsql_cmd=hdbsql_cmd, db=database, file_name=file_name, layer=layer,
                   layer_name=layer_name_str, set_str=set_str, parameter_str=parameter_str,
                   reconfig=reconfig_option))

        # TODO: return the HANA SQL Statement error if sql fails
        self._run_hana_command(cmd)

    def set_ini_parameter(
            self, ini_parameter_values, database, file_name, layer,
            **kwargs):
        """
        Set HANA configuration parameters in ini file

        SQL syntax:
        ALTER SYSTEM ALTER CONFIGURATION (<filename>, <layer>[, <layer_name>])
        SET (<section_name_1>,<parameter_name_1>) = <parameter_value_1>,
            (<section_name_2>,<parameter_name_2>) = <parameter_value_2>
        WITH RECONFIGURE

        key_name or user_name/user_password parameters must be used
        Args:
            ini_parameter_values (list): List containing HANA parameter details
            where each entry is a dictionary like below:
            {'section_name':'name', 'parameter_name':'param_name', 'parameter_value':'value'}
                section_name (str): Section name of parameter in ini file
                parameter_name (str): Name of the parameter to be modified
                parameter_value (str): The value of the parameter to be set
            database (str): Database name
            file_name (str): INI configuration file name
            layer (str): Target layer for the configuration change 'SYSTEM', 'HOST' or 'DATABASE'
            layer_name (str, optional): Target either a tenant name or a target host name
            reconfig (bool, optional): If apply changes to running HANA instance
            key_name (str, optional): Keystore to connect to sap hana db
            user_name (str, optional): User to connect to sap hana db
            user_password (str, optional): Password to connect to sap hana db
        """

        parameter_str = ', '.join("(\'{}\',\'{}\')=\'{}\'".format(
            params['section_name'], params['parameter_name'],
            params['parameter_value']) for params in ini_parameter_values)

        layer_name = kwargs.get('layer_name', None)
        reconfig = kwargs.get('reconfig', False)
        key_name = kwargs.get('key_name', None)
        user_name = kwargs.get('user_name', None)
        user_password = kwargs.get('user_password', None)

        self._manage_ini_file(
            parameter_str=parameter_str, database=database,
            file_name=file_name, layer=layer, layer_name=layer_name,
            set_value=True, reconfig=reconfig, key_name=key_name,
            user_name=user_name, user_password=user_password)

    def unset_ini_parameter(
            self, ini_parameter_names, database, file_name, layer,
            **kwargs):
        """
        Unset HANA configuration parameters in ini file

        SQL syntax:
        ALTER SYSTEM ALTER CONFIGURATION (<filename>, <layer>[, <layer_name>])
        UNSET (<section_name>,<parameter_name>);

        key_name or user_name/user_password parameters must be used
        Args:
            ini_parameter_names (list): List containing HANA parameter details
            where each entry is a dictionary like below:
            {'section_name':'name', 'parameter_name':'param_name'}
                section_name (str): Section name of parameter in ini file
                parameter_name (str): Name of the parameter to be modified
            database (str): Database name
            file_name (str): INI configuration file name
            layer (str): Target layer for the configuration change 'SYSTEM', 'HOST' or 'DATABASE'
            layer_name (str, optional): Target either a tenant name or a target host name
            reconfig (bool, optional): If apply changes to running HANA instance
            key_name (str, optional): Keystore to connect to sap hana db
            user_name (str, optional): User to connect to sap hana db
            user_password (str, optional): Password to connect to sap hana db
        """
        parameter_str = ', '.join("(\'{}\',\'{}\')".format(
            params['section_name'], params['parameter_name']) for params in ini_parameter_names)

        layer_name = kwargs.get('layer_name', None)
        reconfig = kwargs.get('reconfig', False)
        key_name = kwargs.get('key_name', None)
        user_name = kwargs.get('user_name', None)
        user_password = kwargs.get('user_password', None)

        self._manage_ini_file(
            parameter_str=parameter_str, database=database,
            file_name=file_name, layer=layer, layer_name=layer_name,
            set_value=False, reconfig=reconfig, key_name=key_name,
            user_name=user_name, user_password=user_password)
