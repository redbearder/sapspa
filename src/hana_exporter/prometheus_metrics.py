"""
SAP HANA database prometheus data exporter metrics

:author: xarbulu
:organization: SUSE Linux GmbH
:contact: xarbulu@suse.de

:since: 2019-05-09
"""

import logging
import collections
import json


METRICMODEL = collections.namedtuple(
    'Metric',
    'name description labels value unit type enabled hana_version_range'
)


class Metric(METRICMODEL):
    """
    store loaded prometheus metrics from the config/api (structure inherited from namedtuple)
    """

    # pylint:disable=R0913
    # pylint:disable=W0622
    def __new__(cls, name, description, labels, value, unit, type,
                enabled=True, hana_version_range=None):
        if not value:
            raise ValueError('No value specified in metrics.json for {}'.format(name))
        if not hana_version_range:
            hana_version_range = ['1.0.0']
        # lowercase labels and values
        labels = [label.lower() for label in labels]
        value = value.lower()
        return super(Metric, cls).__new__(cls, name, description, labels, value,
                                          unit, type, enabled, hana_version_range)


class Query(object):
    """
    Class to store the query and its metrics
    """

    def __init__(self):
        self.query = None
        self.metrics = []
        self.enabled = True
        self.hana_version_range = ['1.0.0']

    def parse(self, query, query_data):
        """
        Parse metrics by query
        """
        self.query = query
        self.metrics = []
        self.enabled = query_data.get('enabled', True)
        self.hana_version_range = query_data.get('hana_version', ['1.0.0'])
        for metric in query_data['metrics']:
            modeled_data = Metric(**metric)
            self.metrics.append(modeled_data)

    @classmethod
    def get_model(cls, query, metrics):
        """
        Get metric model data
        """
        modeled_query = cls()
        modeled_query.parse(query, metrics)
        return modeled_query


class PrometheusMetrics(object):
    """
    Class to store the metrics data
    """

    def __init__(self, metrics_file):
        self.queries = self.load_metrics(metrics_file)

    @classmethod
    def load_metrics(cls, metrics_file):
        """
        Load metrics file as json
        """
        logger = logging.getLogger(__name__)
        queries = []
        with open(metrics_file, 'r') as file_ptr:
            data = json.load(file_ptr)

        try:
            for query, query_data in data.items():
                modeled_query = Query.get_model(query, query_data)
                queries.append(modeled_query)
        except TypeError as err:
            logger.error('Malformed %s file in query %s ...', metrics_file, query[:50])
            logger.error(str(err))
            raise

        return queries
