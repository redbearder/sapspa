"""
SAP HANA database connector using official dbapi package

How to install:
https://help.sap.com/viewer/1efad1691c1f496b8b580064a6536c2d/Cloud/en-US/39eca89d94ca464ca52385ad50fc7dea.html

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2019-05-08
"""

from hdbcli import dbapi

from shaptools.hdb_connector.connectors import base_connector


class DbapiConnector(base_connector.BaseConnector):
    """
    Class to manage dbapi connection and queries
    """
    def __init__(self):
        super(DbapiConnector, self).__init__()
        self._logger.info('dbapi package loaded')
        self.__properties = {}

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
            properties : Additional properties can be used with named parameters. More info at:
                https://help.sap.com/viewer/0eec0d68141541d1b07893a39944924e/2.0.02/en-US/ee592e89dcce4480a99571a4ae7a702f.html

        Example:
            To avoid automatic reconnection set RECONNECT='FALSE' as parameter
        """
        self._logger.info('connecting to SAP HANA database at %s:%s', host,
                          port)
        self.__properties = kwargs
        try:
            print(self.__properties)
            self._connection = dbapi.connect(
                address=host,
                port=port,
                #user=kwargs.get('user'),
                #password=kwargs.get('password'),
                **self.__properties)
            # self._connection = dbapi.connect(address='127.0.0.1',
            #                                  port=30213,
            #                                  user="HANADB_EXPORTER_USER",
            #                                  password="Abcd1234",
            #                                  DATABASENAME="HD0")
        except dbapi.Error as err:
            raise base_connector.ConnectionError(
                'connection failed: {}'.format(err))
        self._logger.info('connected successfully')

    def query(self, sql_statement):
        """
        Query a sql query result and return a result object
        """
        print(sql_statement)
        self._logger.info('executing sql query: %s', sql_statement)
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(sql_statement)
                result = base_connector.QueryResult.load_cursor(cursor)
        except dbapi.Error as err:
            raise base_connector.QueryError('query failed: {}'.format(err))
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
        Check the connection status

        INFO: Sometimes the state is not changed unless a query is performed

        Returns:
            bool: True if connected False otherwise
        """
        if self._connection:
            return self._connection.isconnected()
        return False

    def reconnect(self):
        """
        Reconnect to the previously connected SAP HANA database if the connection is lost

        The dbapi object str result example:
        <dbapi.Connection Connection object : 10.10.10.10,30015,SYSTEM,Qwerty1234,True>

        """
        if not self._connection:
            raise base_connector.ConnectionError(
                'connect method must be used first to reconnect')
        if not self.isconnected():
            connection_data = str(
                self._connection).split(':')[-1].strip()[:-1].split(',')
            host = connection_data[0]
            port = int(connection_data[1])
            #user = connection_data[2]
            #password = connection_data[3]
            #self.connect(host, port, user=user, password=password, **self._properties)
            self._logger.info('reconnecting...')
            self.connect(host, port, **self.__properties)
        else:
            self._logger.info('connection already created')
