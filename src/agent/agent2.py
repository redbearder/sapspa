#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psutil
import socket
from typing import List, Dict
import os
import re
import json
from prometheus_client import start_http_server, Summary, Counter, Gauge, Histogram, Info, Enum, start_wsgi_server
from prometheus_client import make_wsgi_app
from wsgiref.simple_server import make_server

import random
import time
import requests
import schedule
from configobj import ConfigObj
from optparse import OptionParser
from pyrfc import Connection
import decimal
from decimal import Decimal

instmonfrequency = 30  # seconds


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        from datetime import time
        if isinstance(obj, Decimal):
            return "%.2f" % obj
        if isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        return json.JSONEncoder.default(self, obj)


class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        from datetime import date
        from datetime import time
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        return json.JSONEncoder.default(self, obj)


class JsonCustomEncoder(json.JSONEncoder):
    def default(self, obj):
        from datetime import date
        from datetime import time
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, time):
            return obj.strftime('%H:%M:%S')
        if isinstance(obj, Decimal):
            return "%.2f" % obj
        return json.JSONEncoder.default(self, obj)


class Host(object):
    cpu = None
    mem = None
    swap = None
    hostname = None
    ipaddress: List[Dict] = []

    singleton = None

    def __new__(cls, *args, **kwargs):
        if cls.singleton is None:
            cls.singleton = super().__new__(cls)
        return cls.singleton

    def __init__(self):
        self.cpu = psutil.cpu_count()
        self.mem = psutil.virtual_memory().total
        self.swap = psutil.swap_memory().total
        self.hostname = socket.gethostname()
        ifinfo = psutil.net_if_addrs()
        for key in ifinfo.keys():
            if '127.0.0.1' == ifinfo[key][0].address:
                continue
            ifinfodict = {}
            ifinfodict['device'] = key
            ifinfodict['ip'] = ifinfo[key][0].address
            self.ipaddress.append(ifinfodict)

    @property
    def ipaddressList(self):
        return self.ipaddress

    pass


class Subapp(object):
    sid: List[str] = []

    def __init__(self):
        dirlist = os.listdir('/sapmnt')
        for dir in dirlist:
            if len(dir) == 3:
                self.sid.append(dir)
        pass

    @property
    def sidList(self):
        return self.sid


class Instance(object):
    instance: List[Dict] = []

    def __init__(self, sid):
        profilepath = '/sapmnt/' + sid + '/profile'
        list1 = os.listdir(profilepath)
        for l in list1:
            if '.' not in l and re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l):
                p = {}
                p['profile'] = l
                if 'ASCS' not in l:
                    p['type'] = 'DIALOG'
                    pass
                else:
                    # ASCS
                    p['type'] = 'ASCS'
                    pass
                self.instance.append(p)

    @property
    def instanceList(self):
        return self.instance


class R3rfcconn(object):
    conn = None

    def __init__(self, r3user, r3pwd, r3ashost, r3sysnr, r3client):
        self.conn = Connection(user=r3user,
                               passwd=r3pwd,
                               ashost=r3ashost,
                               sysnr=r3sysnr,
                               client=r3client)

    def get_connection_attributes(self):
        return self.conn.get_connection_attributes()

    def get_function_description(self, func_name):
        return self.conn.get_function_description(func_name)

    def get_table_data(self, tablename: str, offset: int = 0, limit: int = 0):
        read_table_fm = 'RFC_READ_TABLE'
        kwparam = {}
        kwparam['QUERY_TABLE'] = tablename
        kwparam['ROWSKIPS'] = offset
        kwparam['ROWCOUNT'] = limit
        result = self.conn.call(read_table_fm, **kwparam)
        return json.dumps(result, cls=JsonCustomEncoder)

    def get_rfc_data(self, fm: str, **kwparam: dict):
        result = self.conn.call(fm, **kwparam)
        return json.dumps(result, cls=JsonCustomEncoder)

    def get_server_wpinfo(self, servername):
        kwparam = {}
        kwparam['SRVNAME'] = servername
        kwparam['WITH_CPU'] = '00'
        kwparam['WITH_MTX_INFO'] = 0
        kwparam['MAX_ELEMS'] = 0
        return self.get_rfc_data('TH_WPINFO', **kwparam)

    def get_user_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_workprocess_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_bkjob_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_dump_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_rfcresource_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_transport_list(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def get_instance_status(self, servername):
        kwparam = {}
        return self.get_rfc_data('', **kwparam)

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    __version__ = 1
    print('start Monitor agent ok')

    c = Counter('my_failures', 'Description of counter')
    c.inc()  # Increment by 1
    c.inc(1.6)  # Increment by given value

    g = Gauge('my_inprogress_requests', 'Description of gauge')
    g.inc()  # Increment by 1
    g.dec(10)  # Decrement by given value
    g.set(4.2)  # Set to a given value

    s = Summary('request_latency_seconds', 'Description of summary')
    s.observe(4.7)  # Observe 4.7 (seconds in this case)

    h = Histogram('request_latency_seconds_histogram',
                  'Description of histogram')
    h.observe(4.7)  # Observe 4.7 (seconds in this case)

    i = Info('my_build_version', 'Description of info')
    i.info({'version': '1.2.3', 'buildhost': 'foo@bar'})

    app = make_wsgi_app()
    httpd = make_server('', 22331, app)
    httpd.serve_forever()
