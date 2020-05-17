"""
Code to expose some useful methods using the command line

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2019-07-11
"""

import logging
import argparse
import json

from shaptools import hana

PROG = 'shapcli'
LOGGING_FORMAT = '%(message)s'


class DecodedFormatter(logging.Formatter):
    """
    Custom formatter to remove the b'' from the logged text
    """

    def format(self, record):
        message = super(DecodedFormatter, self).format(record)
        if message.startswith('b\''):
            message = message.split('\'')[1]
        return message


class ConfigData(object):
    """
    Class to store the required configuration data
    """

    def __init__(self, data_dict, logger):
        try:
            self.sid = data_dict['sid']
            self.instance = data_dict['instance']
            self.password = data_dict['password']
            self.remote = data_dict.get('remote', None)
        except KeyError as err:
            logger.error(err)
            logger.error('Configuration file must have the sid, instance and password entries')
            raise


def setup_logger(level):
    """
    Setup logging
    """
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = DecodedFormatter(LOGGING_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level=level)
    return logger


def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(PROG)

    parser.add_argument(
        '-v', '--verbosity',
        help='Python logging level. Options: DEBUG, INFO, WARN, ERROR (INFO by default)')
    parser.add_argument(
        '-r', '--remote',
        help='Run the command in other machine using ssh')
    parser.add_argument(
        '-c', '--config',
        help='JSON configuration file with SAP HANA instance data (sid, instance and password)')
    parser.add_argument(
        '-s', '--sid', help='SAP HANA sid')
    parser.add_argument(
        '-i', '--instance', help='SAP HANA instance')
    parser.add_argument(
        '-p', '--password', help='SAP HANA password')

    subcommands = parser.add_subparsers(
        title='subcommands', description='valid subcommands', help='additional help')
    hana_subparser = subcommands.add_parser(
        'hana', help='Commands to interact with SAP HANA databse')
    sr_subparser = subcommands.add_parser(
        'sr', help='Commands to interact with SAP HANA system replication')

    parse_hana_arguments(hana_subparser)
    parse_sr_arguments(sr_subparser)

    args = parser.parse_args()
    return parser, args


def parse_hana_arguments(hana_subparser):
    """
    Parse hana subcommand arguements
    """
    subcommands = hana_subparser.add_subparsers(
        title='hana', dest='hana', help='Commands to interact with SAP HANA databse')
    subcommands.add_parser(
        'is_running', help='Check if SAP HANA database is running')
    subcommands.add_parser(
        'version', help='Show SAP HANA database version')
    subcommands.add_parser(
        'start', help='Start SAP HANA database')
    subcommands.add_parser(
        'stop', help='Stop SAP HANA database')
    subcommands.add_parser(
        'info', help='Show SAP HANA database information')
    subcommands.add_parser(
        'kill', help='Kill all SAP HANA database processes')
    subcommands.add_parser(
        'overview', help='Show SAP HANA database overview')
    subcommands.add_parser(
        'landscape', help='Show SAP HANA database landscape')
    subcommands.add_parser(
        'uninstall', help='Uninstall SAP HANA database instance')
    dummy = subcommands.add_parser(
        'dummy', help='Get data from DUMMY table')
    dummy.add_argument(
        '--key_name',
        help='Keystore to connect to sap hana db '\
        '(if this value is set user, password and database are omitted')
    dummy.add_argument(
        '--user_name', help='User to connect to sap hana db')
    dummy.add_argument(
        '--user_password', help='Password to connect to sap hana db')
    dummy.add_argument(
        '--database', help='Database name to connect')

    hdbsql = subcommands.add_parser(
        'hdbsql', help='Run a sql command with hdbsql')
    hdbsql.add_argument(
        '--key_name',
        help='Keystore to connect to sap hana db '\
        '(if this value is set user, password and database are omitted')
    hdbsql.add_argument(
        '--user_name', help='User to connect to sap hana db')
    hdbsql.add_argument(
        '--user_password', help='Password to connect to sap hana db')
    hdbsql.add_argument(
        '--database', help='Database name to connect')
    hdbsql.add_argument(
        '--query', help='Query to execute')

    user_key = subcommands.add_parser(
        'user', help='Create a new user key')
    user_key.add_argument(
        '--key_name', help='Key name', required=True)
    user_key.add_argument(
        '--environment', help='Database location (host:port)', required=True)
    user_key.add_argument(
        '--user_name', help='User to connect to sap hana db', required=True)
    user_key.add_argument(
        '--user_password', help='Password to connect to sap hana db', required=True)
    user_key.add_argument(
        '--database', help='Database name to connect', required=True)

    backup = subcommands.add_parser(
        'backup', help='Create node backup')
    backup.add_argument(
        '--name', help='Backup file name', required=True)
    backup.add_argument(
        '--database', help='Database name to connect', required=True)
    backup.add_argument(
        '--key_name', help='Key name')
    backup.add_argument(
        '--user_name', help='User to connect to sap hana db')
    backup.add_argument(
        '--user_password', help='Password to connect to sap hana db')


def parse_sr_arguments(sr_subparser):
    """
    Parse hana sr subcommand arguements
    """
    subcommands = sr_subparser.add_subparsers(
        title='sr', dest='sr', help='Commands to interact with SAP HANA system replication')
    state = subcommands.add_parser(
        'state', help='Show SAP HANA system replication state')
    state.add_argument('--sapcontrol', help='Run with sapcontrol', action='store_true')
    status = subcommands.add_parser(
        'status', help='Show SAP HANAsystem replication status')
    status.add_argument('--sapcontrol', help='Run with sapcontrol', action='store_true')
    subcommands.add_parser(
        'disable', help='Disable SAP HANA system replication (to be executed in Primary node)')
    cleanup = subcommands.add_parser(
        'cleanup', help='Cleanup SAP HANA system replication')
    cleanup.add_argument('--force', help='Force the cleanup', action='store_true')
    subcommands.add_parser(
        'takeover', help='Perform a takeover operation (to be executed in Secondary node)')
    enable = subcommands.add_parser(
        'enable', help='Enable SAP HANA system replication primary site')
    enable.add_argument('--name', help='Primary site name', required=True)
    register = subcommands.add_parser(
        'register', help='Register SAP HANA system replication secondary site')
    register.add_argument('--name', help='Secondary site name', required=True)
    register.add_argument('--remote_host', help='Primary site hostname', required=True)
    register.add_argument(
        '--remote_instance', help='Primary site SAP HANA instance number', required=True)
    register.add_argument(
        '--replication_mode', help='System replication replication mode', default='sync')
    register.add_argument(
        '--operation_mode', help='System replication operation mode', default='logreplay')
    unregister = subcommands.add_parser(
        'unregister', help='Unegister SAP HANA system replication secondary site')
    unregister.add_argument('--name', help='Primary site name', required=True)
    copy_ssfs = subcommands.add_parser(
        'copy_ssfs', help='Copy current node ssfs files to other host')
    copy_ssfs.add_argument('--remote_host', help='Other host name', required=True)
    copy_ssfs.add_argument(
        '--remote_password',
        help='Other host SAP HANA instance password (sid and instance must match '\
        'with the current host)', required=True)


# pylint:disable=W0212
def uninstall(hana_instance, logger):
    """
    Uninstall SAP HANA database instance
    """
    logger.info(
        'This command will uninstall SAP HANA instance '\
        'with sid %s and instance number %s (y/n): ',
        hana_instance.sid, hana_instance.inst)
    response = input()
    if response == 'y':
        user = hana.HanaInstance.HANAUSER.format(sid=hana_instance.sid)
        hana_instance.uninstall(user, hana_instance._password)
    else:
        logger.info('Command execution canceled')


def run_hdbsql(hana_instance, hana_args, cmd):
    """
    Run hdbsql command
    """
    hdbsql_cmd = hana_instance._hdbsql_connect(
        key_name=hana_args.key_name,
        user_name=hana_args.user_name,
        user_password=hana_args.user_password)
    cmd = '{hdbsql_cmd} {database}\\"{cmd}\\"'.format(
        hdbsql_cmd=hdbsql_cmd,
        database='-d {} '.format(hana_args.database) if hana_args.database else '',
        cmd=cmd)
    hana_instance._run_hana_command(cmd)

def run_hana_subcommands(hana_instance, hana_args, logger):
    """
    Run hana subcommands
    """
    str_args = hana_args.hana
    if str_args == 'is_running':
        result = hana_instance.is_running()
        logger.info('SAP HANA database running state: %s', result)
    elif str_args == 'version':
        hana_instance.get_version()
    elif str_args == 'start':
        hana_instance.start()
    elif str_args == 'stop':
        hana_instance.stop()
    elif str_args == 'info':
        hana_instance._run_hana_command('HDB info')
    elif str_args == 'kill':
        hana_instance._run_hana_command('HDB kill-9')
    elif str_args == 'overview':
        hana_instance._run_hana_command('HDBSettings.sh systemOverview.py')
    elif str_args == 'landscape':
        hana_instance._run_hana_command('HDBSettings.sh landscapeHostConfiguration.py')
    elif str_args == 'uninstall':
        uninstall(hana_instance, logger)
    elif str_args == 'dummy':
        run_hdbsql(hana_instance, hana_args, 'SELECT * FROM DUMMY')
    elif str_args == 'hdbsql':
        run_hdbsql(hana_instance, hana_args, hana_args.query)
    elif str_args == 'user':
        hana_instance.create_user_key(
            hana_args.key_name, hana_args.environment, hana_args.user_name,
            hana_args.user_password, hana_args.database)
    elif str_args == 'backup':
        hana_instance.create_backup(
            hana_args.database, hana_args.name, hana_args.key_name,
            hana_args.user_name, hana_args.user_password)


def run_sr_subcommands(hana_instance, sr_args, logger):
    """
    Run hana subcommands
    """
    str_args = sr_args.sr
    if str_args == 'state':
        # hana_instance.get_sr_state()
        cmd = 'hdbnsutil -sr_state{}'.format(' --sapcontrol=1' if sr_args.sapcontrol else '')
        hana_instance._run_hana_command(cmd)
    elif str_args == 'status':
        # hana_instance.get_sr_status()
        cmd = 'HDBSettings.sh systemReplicationStatus.py{}'.format(
            ' --sapcontrol=1' if sr_args.sapcontrol else '')
        hana_instance._run_hana_command(cmd, exception=False)
    elif str_args == 'disable':
        hana_instance.sr_disable_primary()
    elif str_args == 'cleanup':
        hana_instance.sr_cleanup(sr_args.force)
    elif str_args == 'takeover':
        hana_instance._run_hana_command('hdbnsutil -sr_takeover')
    elif str_args == 'enable':
        hana_instance.sr_enable_primary(sr_args.name)
    elif str_args == 'register':
        hana_instance.sr_register_secondary(
            sr_args.name, sr_args.remote_host, sr_args.remote_instance,
            sr_args.replication_mode, sr_args.operation_mode)
    elif str_args == 'unregister':
        hana_instance.sr_unregister_secondary(sr_args.name)
    elif str_args == 'copy_ssfs':
        hana_instance.copy_ssfs_files(sr_args.remote_host, sr_args.remote_password)


def load_config_file(config_file, logger):
    """
    Load configuration file data
    """
    with open(config_file, 'r') as f_ptr:
        json_data = json.load(f_ptr)
    return json_data


# pylint:disable=W0212
def run():
    """
    Main execution
    """
    parser, args = parse_arguments()
    logger = setup_logger(args.verbosity or logging.DEBUG)

    # If -c or --config flag is received data is loaded from the configuration file
    if args.config:
        data = load_config_file(args.config, logger)
        config_data = ConfigData(data, logger)
    elif args.sid and args.instance and args.password:
        config_data = ConfigData(vars(args), logger)
    else:
        logger.info(
            'Configuration file or sid, instance and passwords parameters must be provided\n')
        parser.print_help()
        exit(1)

    if args.remote:
        config_data.remote = args.remote

    try:
        hana_instance = hana.HanaInstance(
            config_data.sid, config_data.instance,
            config_data.password, remote_host=config_data.remote)
        if vars(args).get('hana'):
            run_hana_subcommands(hana_instance, args, logger)
        elif vars(args).get('sr'):
            run_sr_subcommands(hana_instance, args, logger)
        else:
            parser.print_help()
    except Exception as err:
        logger.error(err)
        exit(1)


if __name__ == "__main__": # pragma: no cover
    run()
