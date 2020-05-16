"""
SAP HANA database connector factory

:author: xarbulu
:organization: SUSE LLC
:contact: xarbulu@suse.com

:since: 2019-05-08
"""

try:
    from shaptools.hdb_connector.connectors import dbapi_connector
    API = 'dbapi' # pragma: no cover
except ImportError:
    try:
        from shaptools.hdb_connector.connectors import pyhdb_connector
        API = 'pyhdb' # pragma: no cover
    except ImportError:
        from shaptools.hdb_connector.connectors import base_connector
        API = None


class HdbConnector(object):
    """
    HDB factory connector
    """

    # pragma: no cover
    def __new__(cls):
        if API == 'dbapi':
            return dbapi_connector.DbapiConnector() # pragma: no cover
        elif API == 'pyhdb':
            return pyhdb_connector.PyhdbConnector() # pragma: no cover
        raise base_connector.DriverNotAvailableError('dbapi nor pyhdb are installed')
