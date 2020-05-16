"""
SAP HANA database prometheus data exporter

:author: xarbulu
:organization: SUSE Linux GmbH
:contact: xarbulu@suse.de

:since: 2019-05-09
"""

import logging

from prometheus_client import core
from shaptools import hdb_connector
import prometheus_metrics
import utils


class SapHanaCollectors(object):
    """
    SAP HANA database data exporter using multiple db connectors
    """
    def __init__(self, connectors, metrics_file):
        self._logger = logging.getLogger(__name__)
        self._collectors = []
        for connector in connectors:
            collector = SapHanaCollector(connector, metrics_file)
            self._collectors.append(collector)

    def collect(self):
        """
        Collect metrics for each collector
        """
        for collector in self._collectors:
            for metric in collector.collect():
                yield metric


class SapHanaCollector(object):
    """
    SAP HANA database data exporter
    """

    METADATA_LABEL_HEADERS = ['sid', 'insnr', 'database_name']

    def __init__(self, connector, metrics_file):
        self._logger = logging.getLogger(__name__)
        self._hdb_connector = connector
        # metrics_config contains the configuration api/json data
        self._metrics_config = prometheus_metrics.PrometheusMetrics(
            metrics_file)
        self.retrieve_metadata()

    @property
    def metadata_labels(self):
        """
        Get metadata labels data
        """
        return [self._sid, self._insnr, self._database_name]

    def retrieve_metadata(self):
        """
        Retrieve database metadata: sid, instance number, database name and hana version
        """
        query = \
"""SELECT
(SELECT value
FROM M_SYSTEM_OVERVIEW
WHERE section = 'System'
AND name = 'Instance ID') SID,
(SELECT value
FROM M_SYSTEM_OVERVIEW
WHERE section = 'System'
AND name = 'Instance Number') INSNR,
m.database_name,
m.version
FROM m_database m;"""

        self._logger.info('Querying database metadata...')
        query_result = self._hdb_connector.query(query)
        formatted_result = utils.format_query_result(query_result)[0]
        self._hana_version = formatted_result['VERSION']
        self._sid = formatted_result['SID']
        self._insnr = formatted_result['INSNR']
        self._database_name = formatted_result['DATABASE_NAME']
        self._logger.info(
            'Metadata retrieved. version: %s, sid: %s, insnr: %s, database: %s',
            self._hana_version, self._sid, self._insnr, self._database_name)

    def _manage_gauge(self, metric, formatted_query_result):
        """
        Manage Gauge type metric:
        metric is the json.file object for example
        parse a SQL query and fullfill(formatted_query_result) the metric object from prometheus

        Args:
            metric (dict): a dictionary containing information about the metric
            formatted_query_result (nested list): query formated by _format_query_result method
        """
        # Add sid, insnr and database_name labels
        combined_label_headers = self.METADATA_LABEL_HEADERS + metric.labels
        metric_obj = core.GaugeMetricFamily(metric.name, metric.description,
                                            None, combined_label_headers,
                                            metric.unit)
        for row in formatted_query_result:
            labels = []
            metric_value = None
            for column_name, column_value in row.items():
                try:
                    labels.insert(metric.labels.index(column_name.lower()),
                                  column_value)
                except ValueError:  # Received data is not a label, check for the lowercased value
                    if column_name.lower() == metric.value.lower():
                        metric_value = column_value
            if metric_value is None:
                self._logger.warn(
                    'Specified value in metrics.json for metric "%s": (%s) not found or it is '\
                    'invalid (None) in the query result',
                    metric.name, metric.value)
                continue
            elif len(labels) != len(metric.labels):
                # Log when a label(s) specified in metrics.json is not found in the query result
                self._logger.warn(
                    'One or more label(s) specified in metrics.json '
                    'for metric "%s" that are not found in the query result',
                    metric.name)
                continue
            else:
                # Add sid, insnr and database_name labels
                combined_labels = self.metadata_labels + labels
                metric_obj.add_metric(combined_labels, metric_value)
        self._logger.debug('%s \n', metric_obj.samples)
        return metric_obj

    def reconnect(self):
        """
        Reconnect if needed and retrieve new metadata

        hdb_connector reconnect already checks if the connection is working, but we need to
        recheck to run the retrieve_metadata method to update some possible changes
        """
        if not self._hdb_connector.isconnected():
            self._hdb_connector.reconnect()
            self.retrieve_metadata()

    def collect(self):
        """
        execute db queries defined by metrics_config/api file, and store them in
        a prometheus metric_object, which will be served over http for scraping e.g gauge, etc.
        """
        # Try to reconnect if the connection is lost. It will raise an exception is case of error
        self.reconnect()

        for query in self._metrics_config.queries:
            if not query.enabled:
                self._logger.info('Query %s is disabled', query.query)
            elif not utils.check_hana_range(self._hana_version,
                                            query.hana_version_range):
                self._logger.info(
                    'Query %s out of the provided hana version range: %s',
                    query.query, query.hana_version_range)
            else:
                try:
                    query_result = self._hdb_connector.query(query.query)
                except hdb_connector.connectors.base_connector.QueryError as err:
                    self._logger.error('Failure in query: %s, skipping...',
                                       query.query)
                    self._logger.error(str(err))
                    continue  # Moving to the next iteration (query)
                formatted_query_result = utils.format_query_result(
                    query_result)
                if not formatted_query_result:
                    self._logger.warning(
                        'Query %s ... has not returned any record',
                        query.query)
                    continue
                for metric in query.metrics:
                    if metric.type == "gauge":
                        try:
                            metric_obj = self._manage_gauge(
                                metric, formatted_query_result)
                        except ValueError as err:
                            self._logger.error(str(err))
                            # If an a ValueError exception is caught, skip the metric and go on to
                            # complete the rest of the loop
                            continue
                    else:
                        raise NotImplementedError(
                            '{} type not implemented'.format(metric.type))
                    yield metric_obj
