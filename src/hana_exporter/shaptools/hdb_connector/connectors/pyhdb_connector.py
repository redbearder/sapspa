"""
SAP HANA database connector using pyhdb open sourced package

How to install:
https://github.com/SAP/PyHDB

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2019-05-08
"""

import socket
import pyhdb

from shaptools.hdb_connector.connectors import base_connector


class PyhdbConnector(base_connector.BaseConnector):
    """
    Class to manage pyhdb connection and queries
    """

    def __init__(self):
        super(PyhdbConnector, self).__init__()
        self._logger.info('pyhdb package loaded')

    def connect(self, host, port=30015, **kwargs):
        """
        Connect to the SAP HANA database

        # TODO: Add option to connect using the key
        # TODO: Add encryption options

        Args:
            host (str): Host where the database is running
            port (int): Database port (3{inst_number}15 by default)
            user (str): Existing username in the database
            password (str): User password
            timeout (int, optional): Connection and queries timeout in seconds
        """
        self._logger.info('connecting to SAP HANA database at %s:%s', host, port)
        try:
            self._connection = pyhdb.connect(
                host=host,
                port=port,
                user=kwargs.get('user'),
                password=kwargs.get('password')
            )
            self._connection.timeout = kwargs.get('timeout', None)
        except (socket.error, pyhdb.exceptions.DatabaseError) as err:
            raise base_connector.ConnectionError('connection failed: {}'.format(err))
        self._logger.info('connected successfully')

    def query(self, sql_statement):
        """
        Query a sql query result and return a result object
        """
        self._logger.info('executing sql query: %s', sql_statement)
        try:
            cursor = None
            cursor = self._connection.cursor()
            cursor.execute(sql_statement)
            result = base_connector.QueryResult.load_cursor(cursor)
        except pyhdb.exceptions.DatabaseError as err:
            raise base_connector.QueryError('query failed: {}'.format(err))
        finally:
            if cursor:
                cursor.close()
        return result

    def disconnect(self):
        """
        Disconnect from SAP HANA database
        """
        self._logger.info('disconnecting from SAP HANA database')
        self._connection.close()
        self._logger.info('disconnected successfully')

    def isconnected(self):
        """
        Check the connection status. It checks if the socket is properly working

        INFO: Sometimes the state is not changed unless a query is performed

        Returns:
            bool: True if connected False otherwise
        """
        if self._connection and self._connection.isconnected():
            try:
                self._connection._socket.getpeername()
                return True
            except OSError:
                self._logger.error('socket is not correctly working. closing socket')
                self._connection._socket = None
                return False
        return False

    def reconnect(self):
        """
        Reconnect to the previously connected SAP HANA database if the connection is lost
        """
        if not self._connection:
            raise base_connector.ConnectionError('connect method must be used first to reconnect')
        if not self.isconnected():
            # Initialize the socket connection parameters as a new connection will be created
            self._connection.session_id = -1
            self._connection.packet_count = -1
            try:
                self._logger.info('reconnecting...')
                self._connection.connect()
            except (socket.error, pyhdb.exceptions.DatabaseError) as err:
                raise base_connector.ConnectionError('connection failed: {}'.format(err))
        else:
            self._logger.info('connection already created')
