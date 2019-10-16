#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psutil
import socket
from typing import List, Dict
import os
import re
import json
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
    sid: List(str) = []

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
    instance: List(Dict) = []

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

    def get_table_data(self, tablename: str, offset: int = 0, limit: int = 0):
        read_table_fm = 'RFC_READ_TABLE'
        kwparam = {}
        kwparam['QUERY_TABLE'] = tablename
        kwparam['ROWSKIPS'] = offset
        kwparam['ROWCOUNT'] = limit
        result = self.conn.call(read_table_fm, **kwparam)
        return json.dumps(result, cls=JsonCustomEncoder)

    def get_server_wpinfo(self, servername):
        result = self.conn.call('TH_WPINFO',
                                SRVNAME=servername,
                                WITH_CPU='00',
                                WITH_MTX_INFO=0,
                                MAX_ELEMS=0)
        return json.dumps(result, cls=JsonCustomEncoder)

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    __version__ = 1

    print('start Monitor agent ok')
