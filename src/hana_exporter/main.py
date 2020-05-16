import sys
import os
import traceback
import logging
from logging.config import fileConfig
import time
import json
import argparse
import consul
import socket
from typing import List, Dict

from prometheus_client.core import REGISTRY
from prometheus_client import start_http_server

import prometheus_exporter
import db_manager

LOGGER = logging.getLogger(__name__)
CONFIG_FOLDER = '/etc/hana_exporter'
METRICS_FILES = [
    '/etc/hana_exporter/metrics.json', '/usr/etc/hana_exporter/metrics.json'
]


def get_sid_list():
    sidlist: List[str] = []
    try:
        dirlist = os.listdir('/sapmnt')
        for dir in dirlist:
            if len(dir) == 3:
                sidlist.append(dir)
        return sidlist
    except:
        return []


def get_hdb_sid_list():
    sidlist: List[str] = []
    try:
        dirlist = os.listdir('/usr/sap')
        for dir in dirlist:
            if len(dir) == 3:
                if os.path.exists(f'/usr/sap/{dir}/SYS/profile/DEFAULT.PFL'):
                    sidlist.append(dir)

        appsidlist = get_sid_list()
        return list(set(sidlist) - set(appsidlist))
    except:
        return []


def parse_config(config_file):
    """
    Parse config file
    """
    with open(config_file, 'r') as f_ptr:
        json_data = json.load(f_ptr)
    return json_data


def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        "--config",
                        help="Path to hana_exporter configuration file")
    parser.add_argument("-m",
                        "--metrics",
                        help="Path to hana_exporter metrics file")
    parser.add_argument(
        "--identifier",
        help="Identifier of the configuration file from /etc/hana_exporter")
    parser.add_argument(
        "-v",
        "--verbosity",
        help=
        "Python logging level. Options: DEBUG, INFO, WARN, ERROR (INFO by default)"
    )
    args = parser.parse_args()
    return args


def setup_logging(config):
    """
    Setup logging system
    """
    hana_config = config.get('hana')
    sufix = 'hana_exporter_{}_{}'.format(hana_config.get('host'),
                                         hana_config.get('port', 30015))
    log_file = config.get('logging').get('log_file',
                                         '/var/log/{}'.format(sufix))

    fileConfig(config.get('logging').get('config_file'),
               defaults={'logfilename': log_file})

    # The next method is used to recatch and raise all
    # exceptions to redirect them to the logging system
    def handle_exception(*exc_info):  # pragma: no cover
        """
        Catch exceptions to log them
        """
        text = ''.join(traceback.format_exception(*exc_info))
        logging.getLogger('hana_exporter').error(text)

    sys.excepthook = handle_exception


def find_metrics_file():
    """
    Find metrics predefined files in default locations
    """
    for metric_file in METRICS_FILES:
        if os.path.isfile(metric_file):
            return metric_file
    raise ValueError('metrics file does not exist in {}'.format(
        ",".join(METRICS_FILES)))


# Start up the server to expose the metrics.
def run():
    """
    Main execution
    """
    args = parse_arguments()
    if args.config is not None:
        config = parse_config(args.config)
    elif args.identifier is not None:
        config = parse_config('{}/{}.json'.format(CONFIG_FOLDER,
                                                  args.identifier))
    else:
        raise ValueError('configuration file or identifier must be used')

    if config.get('logging', None):
        # setup_logging(config)
        pass
    else:
        logging.basicConfig(level=args.verbosity or logging.INFO)

    if args.metrics:
        metrics = args.metrics
    else:
        metrics = find_metrics_file()

    try:
        # change to use consul
        while True:
            try:
                c = consul.Consul(
                    host=os.environ.get('CONSUL_HOST')
                    if os.environ.get('CONSUL_HOST') else '127.0.0.1',
                    port=23345,
                    scheme='http')
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                c.agent.service.register(name=hostname + '_hana_exporter',
                                         address=ip,
                                         port=23312,
                                         tags=['hana_exporter', 'sapspa'],
                                         enable_tag_override=True)

                break
            except:
                continue

        c = consul.Consul(host=os.environ.get('CONSUL_HOST')
                          if os.environ.get('CONSUL_HOST') else '127.0.0.1',
                          port=23345,
                          scheme='http')
        hana_config = None
        hdbsidlist = get_hdb_sid_list()
        sid = None
        if len(hdbsidlist) == 0:
            exit(0)
        else:
            sid = hdbsidlist[0]
        kvid, kvv = c.kv.get(sid + '_login')

        # hana_config = config['hana']
        dbs = db_manager.DatabaseManager()
        if kvv:
            # get HDB login info from consul
            hana_config = json.loads(kvv['Value'])

            dbs.start(
                hana_config['host'],
                hana_config['port'],
                user=hana_config['user'],
                password=hana_config['password'],
                database=sid,
                # userkey=hana_config['userkey'],
                multi_tenant=config.get('multi_tenant', False),
                timeout=config.get('timeout', 600))
        else:
            dbs.start('127.0.0.1',
                      hana_config.get('port', 30013),
                      userkey="SYSTEMDB",
                      database=sid,
                      multi_tenant=config.get('multi_tenant', False),
                      timeout=config.get('timeout', 600))
    except KeyError as err:
        raise KeyError(
            'Configuration file {} is malformed: {} not found'.format(
                args.config, err))

    connectors = dbs.get_connectors()
    collector = prometheus_exporter.SapHanaCollectors(connectors=connectors,
                                                      metrics_file=metrics)
    REGISTRY.register(collector)
    LOGGER.info('exporter sucessfully registered')

    LOGGER.info('starting to serve metrics')
    start_http_server(config.get('exposition_port', 23312), '0.0.0.0')
    while True:
        time.sleep(1)


if __name__ == "__main__":  # pragma: no cover
    run()
