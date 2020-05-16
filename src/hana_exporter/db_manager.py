"""
SAP HANA database manager

:author: xarbulu
:organization: SUSE Linux GmbH
:contact: xarbulu@suse.de

:since: 2019-10-24
"""

import logging
import time

from shaptools import hdb_connector
import utils

RECONNECTION_INTERVAL = 15


class UserKeyNotSupportedError(ValueError):
    """
    User key not supported error
    """


class DatabaseManager(object):
    """
    Manage the connection to a multi container HANA system
    """

    TENANT_DATA_QUERY =\
"""SELECT DATABASE_NAME,SQL_PORT FROM SYS_DATABASES.M_SERVICES
WHERE COORDINATOR_TYPE='MASTER' AND SQL_PORT<>0"""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._system_db_connector = hdb_connector.HdbConnector()
        self._db_connectors = []

    def _get_tenants_port(self):
        """
        Get tenants port
        """
        data = self._system_db_connector.query(self.TENANT_DATA_QUERY)
        formatted_data = utils.format_query_result(data)
        for tenant_data in formatted_data:
            if tenant_data['DATABASE_NAME'] != 'SYSTEMDB':
                yield tenant_data['DATABASE_NAME'], int(
                    tenant_data['SQL_PORT'])

    def _connect_tenants(self, host, connection_data):
        """
        Connect to the tenants

        Args:
            host (str): Host of the HANA database
            connection_data (dict): Data retrieved from _get_connection_data
        """
        for database, tenant_port in self._get_tenants_port():
            conn = hdb_connector.HdbConnector()
            # If userkey is used database name must be added to connect to tenants
            if connection_data.get('userkey'):
                connection_data['databaseName'] = database
            conn.connect(host, tenant_port, **connection_data)
            self._db_connectors.append(conn)

    def _get_connection_data(self, userkey, user, password, database):
        """
        Check that provided user data is valid. user/password pair or userkey must be provided
        """
        if userkey:
            if hdb_connector.API == 'pyhdb':
                raise UserKeyNotSupportedError(
                    'userkey usage is not supported with pyhdb connector, hdbcli must be installed'
                )
            self._logger.info(
                'stored user key %s will be used to connect to the database',
                userkey)
            if user or password:
                self._logger.warn(
                    'userkey will be used to create the connection. user/password are omitted'
                )
        elif user and password:
            self._logger.info(
                'user/password combination will be used to connect to the databse'
            )
        else:
            raise ValueError(
                'Provided user data is not valid. userkey or user/password pair must be provided'
            )

        return {
            'userkey': userkey,
            'user': user,
            'password': password,
            'DATABASENAME': database,
            'RECONNECT': 'FALSE'
        }

    def start(self, host, port, **kwargs):
        """
        Start de database manager. This will open a connection with the System database and
        retrieve the current environemtn tenant databases data

        Args:
            host (str): Host of the HANA database
            port (int): Port of the System database (3XX13 when XX is the instance number)
            userkey (str): User stored key
            user (str): System database user name (SYSTEM usually)
            password (str): System database user password
            multi_tenant (bool): Connect to all tenants checking the data in the System database
            timeout (int, opt): Timeout in seconds to connect to the System database
        """
        connection_data = self._get_connection_data(
            kwargs.get('userkey', None), kwargs.get('user', ''),
            kwargs.get('password', ''), kwargs.get('database', 'SYSTEMDB'))
        current_time = time.time()
        timeout = current_time + kwargs.get('timeout', 600)
        while current_time <= timeout:
            try:
                # parameters are passed using kwargs to the connect method
                # pyhdb only uses 'user' and `password`
                # dbapi uses 'user', 'password', 'userkey' and other optional params
                self._system_db_connector.connect(host, port,
                                                  **connection_data)
                self._db_connectors.append(self._system_db_connector)
                break
            except hdb_connector.connectors.base_connector.ConnectionError as err:
                self._logger.error(
                    'the connection to the system database failed. error message: %s',
                    str(err))
                # This conditions is used to stop the exporter if the provided userkey is not valid
                if 'Invalid value for KEY' in str(err):
                    raise hdb_connector.connectors.base_connector.ConnectionError(
                        'provided userkey is not valid. Check if dbapi is installed correctly'
                    )
                time.sleep(RECONNECTION_INTERVAL)
                current_time = time.time()
        else:
            raise hdb_connector.connectors.base_connector.ConnectionError(
                'timeout reached connecting the System database')

        if kwargs.get('multi_tenant', True):
            self._connect_tenants(host, connection_data)

    def get_connectors(self):
        """
        Get the connectors
        """
        return self._db_connectors
