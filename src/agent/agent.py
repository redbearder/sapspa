#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
import requests
import schedule
import configobj
import ibm_db
import ibm_db_dbi
import cx_Oracle
import psutil
import pyrfc

cp ../../spdb2mon.cfg .
cp -Rf ../../ibm_db-2.0.6/clidriver .
cp ../../nwrfcsdk/lib/lib* .
cp -Rf ../updatehelper/* .

'''

#global dbconnerrcount
#global r3connerrcount
dbconnerrcount = 0
r3connerrcount = 0

dbmainconn = 1
r3mainconn = 1

r3conn = None

import datetime
import hashlib
import logging
import os
import random
import re
import socket
##########################################################
import string
import sys
import threading
from datetime import *
from logging.handlers import TimedRotatingFileHandler
from urlparse import urlparse

import six
import six.moves.urllib.parse as sixurlparse
import tornado
import tornado.ioloop
import tornado.web
from tornado.options import define, options

try:
    import requests
except ImportError:
    sys.exit("requests not installed. Please install and import")

try:
    import json
except ImportError:
    sys.exit("json not installed. Please install and import")
try:
    import schedule
except ImportError:
    sys.exit("schedule not installed. Please install and import")
try:
    from configobj import ConfigObj
except ImportError:
    sys.exit("configobj not installed. Please install and import")
try:
    from optparse import OptionParser
except ImportError:
    sys.exit("optparse not installed. Please install and import")

try:
    import psutil
    import platform
except ImportError:
    sys.exit("psutil and platform not installed. Please install and import")


try:
    '''Use simplejson if we can, fallback to json otherwise.'''
    import simplejson as json
except ImportError:
    import json  # NOQA



class ObjectDict(dict):
    """Makes a dictionary behave like an object, with attribute-style access.
    """

    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None

    def __setattr__(self, key, value):
        self[key] = value


class WeChatSigner(object):
    """WeChat data signer"""

    def __init__(self, delimiter=b''):
        self._data = []
        self._delimiter = to_binary(delimiter)

    def add_data(self, *args):
        """Add data to signer"""
        for data in args:
            self._data.append(to_binary(data))

    @property
    def signature(self):
        """Get data signature"""
        self._data.sort()
        str_to_sign = self._delimiter.join(self._data)
        return hashlib.sha1(str_to_sign).hexdigest()


def check_signature(token, signature, timestamp, nonce):
    """Check WeChat callback signature, raises InvalidSignatureException
    if check failed.

    :param token: WeChat callback token
    :param signature: WeChat callback signature sent by WeChat server
    :param timestamp: WeChat callback timestamp sent by WeChat server
    :param nonce: WeChat callback nonce sent by WeChat sever
    """
    signer = WeChatSigner()
    signer.add_data(token, timestamp, nonce)
    if signer.signature != signature:
        return False
    else:
        return True


def to_binary(value, encoding='utf-8'):
    """Convert value to binary string, default encoding is utf-8

    :param value: Value to be converted
    :param encoding: Desired encoding
    """
    if not value:
        return b''
    if isinstance(value, six.binary_type):
        return value
    if isinstance(value, six.text_type):
        return value.encode(encoding)
    return six.binary_type(value)



def random_string(length=16):
    rule = string.ascii_letters + string.digits
    rand_list = random.sample(rule, length)
    return ''.join(rand_list)


def get_querystring(uri):
    """Get Querystring information from uri.

    :param uri: uri
    :return: querystring info or {}
    """
    parts = sixurlparse.urlsplit(uri)
    return sixurlparse.parse_qs(parts.query)


###################################################

def killProcessByName(programname):
    os.system("ps -C "+programname+" -o pid=|xargs kill -9")

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

def getOptionMore():
    options = OptionParser(usage='%prog ', description='XSAP SAP monitor agent')
    options.add_option('--sid', '-s', dest="sid", default=sid, help="SAP system SID")
    options.add_option('--dbuser', '-u', dest="dbuser", default=dbuser, help="Database access User for monitoring Database")
    options.add_option('--dbpwd', '-p', dest="dbpwd", default=dbpwd, help="Database access User Password for monitoring Database")
    options.add_option('--posturl', '-l', dest="posturl", default=posturl, help="URL of posting monitor data to Centor collector")
    options.add_option('--monitorid','-i', dest="monitorid", default=monitorid, help="ID for this system monitoring")
    options.add_option('--montype','-t', dest="montype", default='all', help="Monitor type, default value is all, also can use 'db,sap,os,inst' as value instead of 'all' or part of this")
    options.add_option('--proxy', '-x', dest="proxy", default=proxy, help="Agent proxy for accessing Center collector, like 'http://url:port/")
    options.add_option('--r3user', '-U', dest="r3user", default=r3user, help="R3 access user for SAP level monitor")
    options.add_option('--r3pwd', '-P', dest="r3pwd", default=r3pwd, help="R3 access user password for SAP level monitor")
    options.add_option('--r3ashost', '-H', dest="r3ashost", default=r3ashost, help="R3 access Hostname for SAP level monitor")
    options.add_option('--r3sysnr', '-N', dest="r3sysnr", default=r3sysnr, help="R3 access System Instance Number for SAP level monitor")
    options.add_option('--r3client', '-C', dest="r3client", default=r3client, help="R3 access Client for SAP level monitor")
    options.add_option('--configfile', '-f', dest="configfile", default=configfile, help="ConfigFile path for SAP level monitor")
    options.add_option('--damon', '-D', dest="damon", action="store_true", help="ask agent to run as Damon in background")
    opts, args = options.parse_args()

def getOption():
    options = OptionParser(usage='%prog ', description='XSAP SAP monitor agent')
    options.add_option('--damon', '-D', dest="damon", action="store_true", help="ask agent to run as Damon in background")
    opts, args = options.parse_args()

def postData(jsondata):
    global dbmainconn
    global r3mainconn

    import time
    i = 0
    proxies = {
      "http": proxy,
      "https": proxy,
    }
    while True:
        try:
            r = requests.post(posturl, data=jsondata, timeout=10, proxies=proxies)
            log.warning(r.text)
            if r.status_code == 200:
                if r.text == 'from_saprfcmonitor_0':
                    print 'from_saprfcmonitor_0 and r3mainconn = 0, not main r3 conn'
                    log.warning('from_saprfcmonitor_0 and r3mainconn = 0, not main r3 conn')
                    r3mainconn = 0
                    
                if r.text == 'from_dbmonitor_0':
                    print 'from_dbmonitor_0 and dbmainconn = 0, not main db conn'
                    log.warning('from_dbmonitor_0 and dbmainconn = 0, not main db conn')
                    dbmainconn = 0
                return 1
            else:
                print r.text
                # log.warning(r.text)
                if i > 10:
                    print r
                    return 0
                else:
                    i += 1
                    time.sleep(1)
                    continue
        except Exception,e:
            print e
            log.warning(e)
            if i > 10:
                print 'requests postData exception '
                log.warning('requests postData exception')
                return 0
            i += 1
            time.sleep(1)
            continue

#dynamicRemoteFMCall by getting control data from server
def dynamicRemoteFMCall(conn, fnName, paraJsonDict):
    '''
    try:
        para = json.loads(paraJson)
    except ValueError, e:
        return False
    '''
    try:
        result = conn.call(fnName, **paraJsonDict)
        conn.close()
        return json.dumps(result,cls=JsonCustomEncoder)
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''
    pass

def postDynamicRemoteFMCall(postParaJson):
    print 'start to postDynamicRemoteFMCall at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postDynamicRemoteFMCall at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postDynamicRemoteFMCall at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postDynamicRemoteFMCall at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    sid = getConfig('SAP','sid')

    r3user = getConfig('r3','r3user')
    r3pwd = getConfig('r3','r3pwd')
    r3ashost = getConfig('r3','r3ashost')
    r3sysnr = getConfig('r3','r3sysnr')
    r3client = getConfig('r3','r3client')

    global r3connerrcount
    global r3conn
    if r3conn is None or not r3conn.alive:
        try:
            r3conn = Connection(user=r3user, passwd=r3pwd, ashost=r3ashost, sysnr=r3sysnr, client=r3client)
            r3connerrcount = 0
        except Exception,e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    try:
        para = json.loads(postParaJson)
    except ValueError, e:
        return False
    instid = para['instid']
    fmName = para['fmName']
    fmParaArr = para['fmParaArr']
    for fmPara in fmParaArr:
        data = dynamicRemoteFMCall(r3conn,**fmPara)
        metadata = {}
        metadata['instid'] = instid
        metadata['fmName'] = fmName
        metadata['fmPara'] = fmPara
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"dynamicRemoteFMCall", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+data+'", "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)
    #print data
    pass


#this method has been obsolete
#post CMD operation return data
def postCMDReturnData(cmdReturnData, jsonEncode=False):
    print 'start to postCMDReturnData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postCMDReturnData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    sid = getConfig('SAP','sid')

    metadata={}
    metadata['instance']=''
    metadata['cmd']=''
    if jsonEncode:
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"cmdReturnData", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+json.dumps(cmdReturnData,cls=JsonCustomEncoder)+', "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)
    else:
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"cmdReturnData", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+cmdReturnData+', "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)

    #print data
    pass


#getControlCode to operate system
def getControlCode(instanceid):
    import time
    i = 0
    proxies = {
      "http": proxy,
      "https": proxy,
    }
    monitorid = getConfig('XSAP','monitorid')
    controlurlconfig = getConfig('XSAP','controlurl')
    posturl = getConfig('XSAP','posturl')
    url = urlparse(posturl)
    getcontrolcodeurl = url.scheme+'://'+url.hostname+':'+str(url.port)+'/'+'mon/control'
    if controlurlconfig!='':
        getcontrolcodeurl = controlurlconfig

    rooturlconfig = getConfig('XSAP','rooturl')
    if rooturlconfig!='':
        getcontrolcodeurl = rooturlconfig+'mon/control'
    urlpara = {'monitorid':monitorid , 'instanceid': instanceid}
    while True:
        try:
            r = requests.get(getcontrolcodeurl, params=urlpara, timeout=10, proxies=proxies)
            #print r.url
            if r.status_code == 200:
                return r.text
            else:
                if i > 10:
                    print r
                    return '0'
                else:
                    i += 1
                    time.sleep(1)
                    continue
        except Exception,e:
            print e
            if i > 10:
                print 'requests getControlCode exception '
                log.warning('requests getControlCode exception')
                return '0'
            i += 1
            time.sleep(1)
            continue


#getControlCommand to operate system
def getControlCommand(instanceid):
    import time
    i = 0
    proxies = {
      "http": proxy,
      "https": proxy,
    }
    monitorid = getConfig('XSAP','monitorid')
    commandurlconfig = getConfig('XSAP','commandurl')
    posturl = getConfig('XSAP','posturl')
    url = urlparse(posturl)
    getcontrolcmdurl = url.scheme+'://'+url.hostname+':'+str(url.port)+'/'+'mon/command'
    if commandurlconfig!='':
        getcontrolcmdurl = commandurlconfig

    rooturlconfig = getConfig('XSAP','rooturl')
    if rooturlconfig!='':
        getcontrolcmdurl = rooturlconfig+'mon/command'
    urlpara = {'monitorid':monitorid , 'instanceid': instanceid}
    while True:
        try:
            r = requests.get(getcontrolcmdurl, params=urlpara, timeout=10, proxies=proxies)
            #print r.url
            if r.status_code == 200:
                return r.text
            else:
                if i > 10:
                    print r
                    return '0'
                else:
                    i += 1
                    time.sleep(1)
                    continue
        except Exception,e:
            print e
            if i > 10:
                print 'requests getControlCommand exception '
                log.warning('requests getControlCommand exception')
                return '0'
            i += 1
            time.sleep(1)
            continue


#getControlRFC to call system RFC
def getControlRFC(instanceid):
    import time
    i = 0
    proxies = {
      "http": proxy,
      "https": proxy,
    }
    monitorid = getConfig('XSAP','monitorid')
    rfcurlconfig = getConfig('XSAP','rfcurl')
    posturl = getConfig('XSAP','posturl')
    url = urlparse(posturl)
    getcontrolrfcurl = url.scheme+'://'+url.hostname+':'+str(url.port)+'/'+'mon/rfc'
    if rfcurlconfig!='':
        getcontrolrfcurl = rfcurlconfig

    rooturlconfig = getConfig('XSAP','rooturl')
    if rooturlconfig!='':
        getcontrolrfcurl = rooturlconfig+'mon/rfc'
    urlpara = {'monitorid':monitorid , 'instanceid': instanceid}
    while True:
        try:
            r = requests.get(getcontrolrfcurl, params=urlpara, timeout=10, proxies=proxies)
            #print r.url
            if r.status_code == 200:
                return r.text
            else:
                if i > 10:
                    print r
                    return 0
                else:
                    i += 1
                    time.sleep(1)
                    continue
        except Exception,e:
            print e
            if i > 10:
                print 'requests getControlCommand exception '
                log.warning('requests getControlCommand exception')
                return 0
            i += 1
            time.sleep(1)
            continue

#OS Monitor data
def postOSMonData():
    print 'start to postOSMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postOSMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    stat = {}
    cpustat = {}
    memstat = {}
    diskstat = []

    cpu_percent_all = psutil.cpu_percent()
    cpustat['cpu_percent_all'] = cpu_percent_all
    cpu_times_percent = psutil.cpu_times_percent()
    cpustat['cpu_percent_user'] = cpu_times_percent.user
    cpustat['cpu_percent_system'] = cpu_times_percent.system
    if platform.system() != 'Windows':
        cpustat['cpu_percent_user'] = cpu_times_percent.iowait

    virtual_memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    memstat['virtual_memory_total'] = virtual_memory.total
    memstat['virtual_memory_free'] = virtual_memory.free
    memstat['virtual_memory_percent'] = virtual_memory.percent

    memstat['swap_memory_total'] = swap_memory.total
    memstat['swap_memory_free'] = swap_memory.free
    memstat['swap_memory_percent'] = swap_memory.percent

    disk_partitions = psutil.disk_partitions()
    for partition in disk_partitions:
        if partition.mountpoint in fsexclude:
            continue
        diskdict = {}
        diskdict['device'] = partition.device
        diskdict['mountpoint'] = partition.mountpoint
        disk_usage = psutil.disk_usage(diskdict['mountpoint'])
        diskdict['disk_usage_total'] = disk_usage.total
        diskdict['disk_usage_free'] = disk_usage.free
        diskdict['disk_usage_percent'] = disk_usage.percent
        diskstat.append(diskdict)
    pass


    #print cpustat
    #print memstat
    #print diskstat

    stat['cpustat'] = cpustat
    stat['memstat'] = memstat
    stat['diskstat'] = diskstat

    encodedjson = json.dumps(stat)

    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"os", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "hostname":"'+socket.gethostname()+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
    #print jsondata
    print postData(jsondata)

def getInstMonData():
    print 'start to getInstMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to getInstMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    hostname = socket.gethostname()
    sid = getConfig('SAP','sid')
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            instname = arr[1]
            localinstancelist.append(instname)
            pass
    inststatuslist = []
    for instance in localinstancelist:
        cmd = 'tail -1 /usr/sap/'+sid+'/'+instance+'/work/available.log'
        status = os.popen(cmd).readline()
        if status.find('Available') == -1:
            print 'Stoped'
            log.info('Stoped')
            inststatus = {"inst":sid+"_"+instance+"_"+hostname,"status":"Stoped"}
        else:
            print 'Started'
            log.info('Started')
            inststatus = {"inst":sid+"_"+instance+"_"+hostname,"status":"Started"}
        inststatuslist.append(inststatus)
        pass
    return inststatuslist
    pass

def postInstMonData():
    data = getInstMonData()
    encodedjson = json.dumps(data)
    #print encodedjson
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"inst", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}

    print postData(jsondata)
    pass

#get OS profile list
def getProfileList(sid):
    #get profile path
    profilepath = '/sapmnt/'+sid+'/profile'
    profilelist = []
    try:
        list1 = os.listdir(profilepath)
        for l in list1:
            if '.' not in l and re.match(sid+'_[A-Z0-9]+_[a-zA-Z0-9]+', l):
                profilelist.append(l)
    except Exception,e:
        print e
        print 'get profile list fail'
        log.warning(e)
        log.warning('get profile list fail')
    return list(set(profilelist))
    pass

#get SAP system server instance name list
def getServerInstanceList(sid):
    serverinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if 'ASCS' not in p:
            arr = p.split('_')
            i = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            serverinstancelist.append(i)
            pass
    return serverinstancelist
    pass


#CNV_MBT_ADM_WP_TOTAL_ACTIVITY RFC
def getWPTotalActivity(conn):
    try:
        result = conn.call('CNV_MBT_ADM_WP_TOTAL_ACTIVITY')
        conn.close()
        return json.dumps(result,cls=JsonCustomEncoder)
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''
    pass

def postWPTotalActivity():
    print 'start to postWPTotalActivity at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postWPTotalActivity at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postWPTotalActivity at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postWPTotalActivity at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    sid = getConfig('SAP','sid')

    r3user = getConfig('r3','r3user')
    r3pwd = getConfig('r3','r3pwd')
    r3ashost = getConfig('r3','r3ashost')
    r3sysnr = getConfig('r3','r3sysnr')
    r3client = getConfig('r3','r3client')

    global r3connerrcount
    global r3conn
    if r3conn is None or not r3conn.alive:
        try:
            r3conn = Connection(user=r3user, passwd=r3pwd, ashost=r3ashost, sysnr=r3sysnr, client=r3client)
            r3connerrcount = 0
        except Exception,e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    data = getWPTotalActivity(r3conn)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"wpTotalActivity", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+data+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    #print data
    pass

#TH_WPINFO RFC
def getWPInfoByServerName(conn,servername):
    try:
        result = conn.call('TH_WPINFO', SRVNAME=servername, WITH_CPU='00', WITH_MTX_INFO=0, MAX_ELEMS=0)
        conn.close()
        return json.dumps(result,cls=JsonCustomEncoder)
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''
    pass

def postWPInfo():
    print 'start to postWPInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postWPInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postWPInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postWPInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    sid = getConfig('SAP','sid')

    r3user = getConfig('r3','r3user')
    r3pwd = getConfig('r3','r3pwd')
    r3ashost = getConfig('r3','r3ashost')
    r3sysnr = getConfig('r3','r3sysnr')
    r3client = getConfig('r3','r3client')

    global r3connerrcount
    global r3conn
    if r3conn is None or not r3conn.alive:
        try:
            r3conn = Connection(user=r3user, passwd=r3pwd, ashost=r3ashost, sysnr=r3sysnr, client=r3client)
            r3connerrcount = 0
        except Exception,e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    instancelist = getServerInstanceList(sid)
    for i in instancelist:
        data = getWPInfoByServerName(r3conn,i)
        metadata = {}
        metadata['instancename'] = i
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"wpInfo", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+data+', "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)
        pass

    #print data
    pass

#ST03 monitor statics data
def getSAPTuneSummaryStatistic(conn):
    try:
        result = conn.call('SAPTUNE_GET_SUMMARY_STATISTIC')
        conn.close()
        return json.dumps(result,cls=JsonCustomEncoder)
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''

    pass

def postSAPTuneSummaryStatistic(conn):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postSAPTuneSummaryStatistic at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postSAPTuneSummaryStatistic at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    data = getSAPTuneSummaryStatistic(conn)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"wpTotalActivity", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+data+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    #print data
    pass

def getST03Summary(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    #result = conn.call('SAPWL_WORKLOAD_GET_SUMMARY', PERIODTYPE='D',HOSTID='PEKAX198',STARTDATE=datetime.strptime('20160302', '%Y%m%d'),INSTANCE='PEKAX198_CI2_01')
    try:
        result = conn.call('SAPWL_WORKLOAD_GET_SUMMARY', PERIODTYPE=PERIODTYPE,HOSTID=HOSTID,STARTDATE=DATESTR,INSTANCE=INSTANCE)
        conn.close()
        return json.dumps(result,cls=DecimalEncoder)
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''

    pass

def postST03Summary(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03Summary at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03Summary at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    #list /sapmnt/SID/profile and analyze to HOSTID, INSTANCE, DATESTR
    data = getST03Summary(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapst03summary", "datetime":"'+datetime.strptime(DATESTR, '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S')+'", "instance":"'+INSTANCE+'", "data":'+data+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    #print data
    pass

def getST03Statistic(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    try:
        result = conn.call('SAPWL_WORKLOAD_GET_STATISTIC', PERIODTYPE=PERIODTYPE,HOSTID=HOSTID,STARTDATE=DATESTR,INSTANCE=INSTANCE)
        conn.close()
        return json.dumps(result,cls=DecimalEncoder,encoding="ISO-8859-1")
    except Exception,e:
        conn.close()
        log.warning(e)
        return ''

    pass

def postST03Statistic(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03Statistic at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03Statistic at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    #list /sapmnt/SID/profile and analyze to HOSTID, INSTANCE, DATESTR
    data = getST03Statistic(conn,HOSTID, INSTANCE, DATESTR, PERIODTYPE)
    #print len(data)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapst03statistic", "datetime":"'+datetime.strptime(DATESTR, '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S')+'", "instance":"'+INSTANCE+'", "data":'+data+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    #print data
    pass

def postST03MonData():
    print 'start to postST03MonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postST03MonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03MonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03MonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    sid = getConfig('SAP','sid')

    r3user = getConfig('r3','r3user')
    r3pwd = getConfig('r3','r3pwd')
    r3ashost = getConfig('r3','r3ashost')
    r3sysnr = getConfig('r3','r3sysnr')
    r3client = getConfig('r3','r3client')

    global r3connerrcount
    global r3conn
    if r3conn is None or not r3conn.alive:
        try:
            r3conn = Connection(user=r3user, passwd=r3pwd, ashost=r3ashost, sysnr=r3sysnr, client=r3client)
            r3connerrcount = 0
        except Exception,e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return
    #profilelist = []
    st03instancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if 'ASCS' not in p:
            arr = p.split('_')
            i = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            st03instancelist.append(i)
            pass
    for i in st03instancelist:
            hostid = i.split('_')[0]
            yesterday = datetime.now()+timedelta(days=-1)
            datestr = yesterday.strftime('%Y%m%d')
            instance = i
            try:
                postST03Summary(r3conn,hostid, instance, datestr)
                postST03Statistic(r3conn,hostid, instance, datestr)
            except Exception,e:
                log.warning(e)
                log.warning(instance+' data is not exist yet or RFC connection error')
                print instance+' data is not exist yet or RFC connection error'

def getJobStatR(date,time):
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to getJobStatR at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to getJobStatR at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='R'"
    sql = "select * from "+dbschema+".V_OP where STATUS='R'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getJobStatF(date,time):
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='F'"
    sql = "select * from "+dbschema+".V_OP where ENDDATE='"+date+"' and ENDTIME>'"+time+"' and STATUS='F'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getJobStatA(date,time):
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='A'"
    sql = "select * from "+dbschema+".V_OP where ENDDATE='"+date+"' and ENDTIME>'"+time+"' and STATUS='A'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getDumpNum(date): #date format is 20160223
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    conn = ibm_db.connect(dsn, '', '', conn_options)
    sql = "select * from "+dbschema+".SNAP where SEQNO='000' and DATUM='"+date+"'"
    stmt = ibm_db.exec_immediate(conn, sql)
    row = ibm_db.fetch_row(stmt)
    DUMPNUM = ibm_db.result(stmt, "DUMPNUM")
    ibm_db.close(conn)
    return DUMPNUM
    ''''
    sql = "select count(*) as DUMPNUM from SNAP where SEQNO='000' and DATUM='"+date+"'"
    stmt = getResult(sql)
    row = ibm_db.fetch_row(stmt)
    DUMPNUM = ibm_db.result(stmt, "DUMPNUM")
    return DUMPNUM
    '''
    pass

def getTodayDumpNum(): #date format is 20160223
    date = datetime.now().strftime('%Y%m%d')
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    conn = ibm_db.connect(dsn, '', '', conn_options)
    sql = "select count(*) as DUMPNUM from "+dbschema+".SNAP where SEQNO='000' and DATUM='"+date+"'"
    stmt = ibm_db.exec_immediate(conn, sql)
    row = ibm_db.fetch_row(stmt)
    DUMPNUM = ibm_db.result(stmt, "DUMPNUM")
    ibm_db.close(conn)
    return DUMPNUM
    pass

def getTodayDump(): #date format is 20160223
    filepath = '/tmp/querytodaydump.time'
    if not os.path.isfile(filepath): #如果不存在就返回False
        savetimefile = open(filepath, 'w+')
        savetimefile.close( )
    savetimefile = open(filepath, 'r')
    savetime = savetimefile.read()
    if savetime == '':
        lastdate = datetime.now().strftime('%Y%m%d')
        lasttime = '000000'
    else:
        thattime = time.strptime(savetime, "%Y-%m-%d %H:%M:%S.%f")
        lastdate = time.strftime('%Y%m%d',thattime)
        lasttime = time.strftime('%H%M%S',thattime)
        pass

    #date = datetime.now().strftime('%Y%m%d')
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from "+dbschema+".SNAP where SEQNO='000' and DATUM='"+date+"'"
    sql = "select * from "+dbschema+".SNAP where SEQNO='000' and DATUM='"+lastdate+"' and UZEIT>'"+lasttime+"'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)

        savetimefile = open(filepath, 'w')
        if datetime.now().strftime('%Y%m%d') != lastdate:
            savetime = datetime.now().strftime('%Y-%m-%d 00:00:00.000000')
            savetimefile.write(savetime)
            pass
        else:
            savetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            savetimefile.write(savetime)
            pass
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)

    return result
    pass

def getNewJobStat():
    filepath = '/tmp/queryjobstat.time'
    if not os.path.isfile(filepath): #如果不存在就返回False
        savetimefile = open(filepath, 'w+')
        savetimefile.close( )
    #savetimefile = open(os.path.dirname(os.path.abspath(__file__))+'/queryjobstat.time', 'w')
    savetimefile = open(filepath, 'r')
    savetime = ''
    lastdate = ''
    lasttime = ''
    data = {}
    try:
        savetime = savetimefile.read()
        if savetime == '':
            lastdate = datetime.now().strftime('%Y%m%d')
            lasttime = '000000'
        else:
            thattime = time.strptime(savetime, "%Y-%m-%d %H:%M:%S.%f")
            lastdate = time.strftime('%Y%m%d',thattime)
            lasttime = time.strftime('%H%M%S',thattime)
            pass

        dataf = getJobStatF(lastdate,lasttime)
        datar = getJobStatR(lastdate,lasttime)
        dataa = getJobStatA(lastdate,lasttime)

        data = {}
        data['jobf'] = dataf
        data['jobr'] = datar
        data['joba'] = dataa

        savetimefile = open(filepath, 'w')
        if datetime.now().strftime('%Y%m%d') != lastdate:
            savetime = datetime.now().strftime('%Y-%m-%d 00:00:00.000000')
            savetimefile.write(savetime)
            pass
        else:
            savetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            savetimefile.write(savetime)
            pass
        return data
    except Exception, e:
        print e
        log.warning(e)
        #raise e
        return data
    finally:
         savetimefile.close( )

def getSnapLock():
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    sql = "select AGENT_ID,LOCK_OBJECT_TYPE,LOCK_NAME,LOCK_COUNT,LOCK_MODE,TABNAME,TBSP_NAME from sysibmadm.SNAPLOCK order by LOCK_COUNT desc fetch first 5 rows only"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount  = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)

    return result
    pass

def getHotTable():
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    sql = "select substr(tabschema,1,15) as tabschema,substr(tabname,1,15) as tabname,TAB_TYPE,TABLE_SCANS,ROWS_READ,(ROWS_INSERTED+ROWS_UPDATED+ROWS_DELETED) as rows_IUD from table(MON_GET_TABLE(null,null,null)) order by rows_read desc fetch first 30 rows only"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getTopExecTimeSql():
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    sql = "select NUM_EXECUTIONS,AVERAGE_EXECUTION_TIME_S,STMT_TEXT from sysibmadm.TOP_DYNAMIC_SQL order by AVERAGE_EXECUTION_TIME_S desc fetch first 5 rows only"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getMutiBusySql():
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    sql = "select num_exec_with_metrics as num_exec, total_cpu_time/num_exec_with_metrics as avg_time, total_act_time,total_act_time/num_exec_with_metrics as act_time,total_act_wait_time/num_exec_with_metrics as wait_time,rows_read, rows_returned, rows_modified, lock_wait_time, stmt_Text as stmt_text from table(mon_get_pkg_cache_stmt('D', NULL, NULL, -2)) as T where t.num_exec_with_metrics > 10 order by t.total_cpu_time desc fetch first 30 rows only"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def getBackupLastday():
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT : ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    sql = "select distinct SQLCODE,timestampdiff(4,char(timestamp(end_time)-timestamp(start_time)))  as Elapsed_Time_min,  substr(firstlog,1,13) as Start_Log, substr(lastlog,1,13) as End_Log,  num_tbsps as Number_Tbspcs,  case(operationType)  when 'F' then 'Offline_Full'  when 'N' then 'Online_Full'  when 'I' then 'Offline_Incremental'  when 'O' then 'Online_Incremental'  when 'D' then 'Offline_Delta'  when 'E' then 'Online_Delta'  else '?'  end as Type,  date(timestamp(end_time)) as Day_Completed,  time(timestamp(end_time)) as Time_Completed  from sysibmadm.db_history  where operation = 'B' and timestamp(end_time) > current_timestamp - 24 hours order by Day_Completed desc fetch first 1 row only"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row  = ibm_db.fetch_assoc( stmt )
        i=0
        dbconnerrcount  = 0
        while( row ):
            result.append( row )
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception, e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass

def postTodayDumpNum():
    data = getTodayDumpNum()
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapdump", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+str(data)+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    pass

def postTodayDump():
    data = getTodayDump()
    encodedjson = json.dumps(data)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapdump", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
    print postData(jsondata)
    pass

def postNewJobStat():
    data = getNewJobStat()
    encodedjson = json.dumps(data)
    #print encodedjson
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapjob", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}

    print postData(jsondata)
    pass

def postDbMon():
    data1 = getTopExecTimeSql()
    data2 = getSnapLock()
    data3 = getHotTable()
    encodedjson1 = json.dumps(data1)
    encodedjson2 = json.dumps(data2)
    encodedjson3 = json.dumps(data3)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"db", "dbtype":"db2", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":{"topsql":'+encodedjson1+',"snaplock":'+encodedjson2+',"hottable":'+encodedjson3+'}, "from":"'+socket.gethostname()+'"}'}

    print postData(jsondata)
    #print data1
    pass

def postDbBackupMon():
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to postDbBackupMon at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to postDbBackupMon at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    data3 = getBackupLastday()
    encodedjson3 = json.dumps(data3,cls=DatetimeEncoder)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"dbbackup", "dbtype":"db2", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":{"backup":'+encodedjson3+'}, "from":"'+socket.gethostname()+'"}'}

    print postData(jsondata)
    #print data1
    pass

def postMutiBusySql():
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to postMutiBusySql at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to postMutiBusySql at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    data3 = getMutiBusySql()
    encodedjson3 = json.dumps(data3,cls=DatetimeEncoder)
    jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"dbmutibusysql", "dbtype":"db2", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":{"dbmutibusysql":'+encodedjson3+'}, "from":"'+socket.gethostname()+'"}'}

    print postData(jsondata)
    #print data1
    pass


#abap and both
def postDBMonData():
    print 'start to postDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to postDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to postDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    postNewJobStat()
    #postTodayDumpNum()
    postTodayDump()
    postDbMon()
    pass

#java
#abap and both
def postJavaDBMonData():
    print 'start to postJavaDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postJavaDBMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    postDbMon()
    pass

### SAP and System control operation
def sapInstController():
    import commands
    print 'start to sapInstController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to sapInstController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    hostname = socket.gethostname()
    sid = getConfig('SAP','sid').upper()
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            instname = arr[1]
            localinstancelist.append(instname)
            pass
    for instance in localinstancelist:
        #get control code from url
        #hostctrl to start and stop sap
        codejson = getControlCode(instance)
        if codejson == '0':
            continue
        #print 'code is '+code
        #code is json
        try:
            codedecode = json.loads(codejson)
        except Exception,e:
            log.error(e)
            continue
        instid = codedecode['instid']
        code = codedecode['controlcode']
        control = codedecode['control']
        nr = instance[-2:]
        #print 'nr is '+nr
        if code == '1':
            #start
            print 'cleanipc'
            os.system('su - '+sid.lower()+'adm -c "cleanipc '+nr+' remove"')
            print 'start instace'
            log.info('start instace')
            #os.system('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Start')
            (status, output) = commands.getstatusoutput('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Start')
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapcontrolReturnData", "metadata":'+json.dumps(codedecode,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+json.dumps(output,cls=JsonCustomEncoder)+'", "from":"'+socket.gethostname()+'"}'}
            print postData(jsondata)
            pass
        if code == '2':
            #stop
            print 'stop instace'
            log.info('stop instace')
            #os.system('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Stop')
            (status, output) = commands.getstatusoutput('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Stop')
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"sapcontrolReturnData", "metadata":'+json.dumps(codedecode,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+json.dumps(output,cls=JsonCustomEncoder)+'", "from":"'+socket.gethostname()+'"}'}
            print postData(jsondata)
            pass
        pass
    pass

def cmdController():
    print 'start to cmdController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to cmdController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    import commands
    hostname = socket.gethostname()
    sid = getConfig('SAP','sid').upper()
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            instname = arr[1]
            localinstancelist.append(instname)
            pass
    for instance in localinstancelist:
        #get control cmd from url
        cmdjsondata = getControlCommand(instance)
        if cmdjsondata == '0':
            continue

        try:
            cmddict = json.loads(cmdjsondata)
        except Exception,e:
            continue
        nr = instance[-2:]
        cmd = cmddict['cmd']
        instid = cmddict['instid']
        jsonEncode = cmddict['jsonEncode']
        #do cmd and post return
        (status, output) = commands.getstatusoutput(str(cmd))
        print 'start to postCMDReturnData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('start to postCMDReturnData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        metadata={}
        metadata['instid']=instid
        metadata['cmd']=cmd
        metadata['status']=status
        if jsonEncode:
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"cmdReturnData", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+json.dumps(output,cls=JsonCustomEncoder)+', "from":"'+socket.gethostname()+'"}'}
            print postData(jsondata)
        else:
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"cmdReturnData", "metadata":'+json.dumps(metadata,cls=JsonCustomEncoder)+', "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+output+'", "from":"'+socket.gethostname()+'"}'}
            if getConfig('XSAP','debug'):
                log.info(jsondata)
            print postData(jsondata)

        pass
    pass

def rfcController():
    print 'start to rfcController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to rfcController at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    import commands
    hostname = socket.gethostname()
    sid = getConfig('SAP','sid').upper()
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
            instname = arr[1]
            localinstancelist.append(instname)
            pass
    for instance in localinstancelist:
        #get control rfc from url
        rfcjsondata = getControlRFC(instance)
        if rfcjsondata == '0':
            continue
        nr = instance[-2:]
        #do call rfc and post return
        postDynamicRemoteFMCall(rfcjsondata)
        pass
    pass

def createScheduler():
    schedule.every(int(dbmonfrequency)).minutes.do(postDBMonData)
    schedule.every(int(osmonfrequency)).minutes.do(postOSMonData)
    #schedule.every().hour.do(job)
    schedule.every().day.at(sapst03montime).do(postST03MonData)
    #schedule.every().monday.do(job)
    #schedule.every().wednesday.at("13:15").do(job)

def getRootUrlConfig(configfile='spdb2mon.cfg'):
    try:
        config = ConfigObj(configfile)
        sec = config['XSAP']
        v = sec['rooturl']
        return  v
    except Exception,e:
        return 'http://api.sapper.cn/'

def getConfig(section, key, configfile='spdb2mon.cfg'):
    try:
        config = ConfigObj(configfile)
        sec = config[section]
        v = sec[key]
        return  v
        '''
        #[XSAP]
        XSAP = config['XSAP']
        posturl = XSAP['posturl']
        monitorid = XSAP['monitorid']
        montype = XSAP['montype']
        proxy = XSAP['proxy']
        #[SAP]
        SAP = config['SAP']
        sid = SAP['sid']
        #[db]
        db = config['db']
        database = sid
        dbuser = db['dbuser']
        dbpwd = db['dbpwd']
        dbhost = db['dbhost']
        dbport = db['dbport']
        dsn = "DATABASE="+sid+";HOSTNAME="+dbhost+";PORT="+dbport+";PROTOCOL=TCPIP;UID="+dbuser+";PWD="+dbpwd+";"
        #[r3]
        r3 = config['r3']
        r3user = r3['r3user']
        r3pwd = r3['r3pwd']
        r3ashost = r3['r3ashost']
        r3sysnr = r3['r3sysnr']
        r3client = r3['r3client']
        #[frequency]
        frequency = config['frequency']
        osmonfrequency = frequency['osmonfrequency']
        dbmonfrequency = frequency['dbmonfrequency']
        sapjobmonfrequency = frequency['sapjobmonfrequency']
        sapdumpmonfrequency = frequency['sapdumpmonfrequency']
        sapst03montime = frequency['sapst03montime']
        '''
    except Exception,e:
        if key =='rooturl':
            return 'http://api.sapper.cn/'
        if key =='posturl':
            return getRootUrlConfig()+'mon/collect'
        if key =='controlurl':
            return ''
        if key =='commandurl':
            return ''
        if key =='rfcurl':
            return ''
        if key =='updatetime':
            return ''
        if key =='updateurl':
            return ''
        if key =='debug':
            return 0
        if key =='systype':
            return 'abap'
        print 'Configuration '+str(e)+' is missing'
        print 'please fulfill Configuration in spdb2mon.cfg file with Same Path'
        log.warning(e)
        log.warning('Configuration '+str(e)+' is missing')
        log.warning('please fulfill Configuration in spdb2mon.cfg file with Same Path')
        sys.exit(0)
    pass

def updateHelper(updateurl,version,programname,identification,proxy=None):
    #start another process to check
    #if new update, terminate mon agent process
    #download and uncompress update.zip in current DIR
    #then sys.exit(0)
    #start mon agent process background
    #exec updatehelper
    print 'check update'
    log.info('check update')
    if proxy:
        os.system('./updatehelper --url='+updateurl+' --version='+str(version)+' --program='+programname+' --identification='+identification+' --proxy='+proxy+' >>updatehelper.log &')
        pass
    else:
        os.system('./updatehelper --url='+updateurl+' --version='+str(version)+' --program='+programname+' --identification='+identification+' >>updatehelper.log &')
        pass
    pass

def createDaemon():
    #Funzione che crea un demone per eseguire un determinato programma

    import os

    # create - fork 1
    try:
        if os.fork() > 0:
            os._exit(0) # exit father
    except OSError, error:
        print 'fork #1 failed: %d (%s)' % (error.errno, error.strerror)
        os._exit(1)

    # it separates the son from the father
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # create - fork 2
    try:
        pid = os.fork()
        if pid > 0:
            print 'Daemon PID %d' % pid
            os._exit(0)
    except OSError, error:
        print 'fork #2 failed: %d (%s)' % (error.errno, error.strerror)
        os._exit(1)

    #funzioneDemo() # function demo

def postConnerrMonData():
    print 'start to postConnerrMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log.info('start to postConnerrMonData at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global dbconnerrcount
    global r3connerrcount
    connerrthreshold = 10
    if dbconnerrcount > connerrthreshold:
        log.warning('connerr is dbconnerrcount > connerrthreshold at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        conn = 'db'
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"connerr", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+conn+'", "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)
        pass
    if r3connerrcount > connerrthreshold:
        log.warning('connerr is r3connerrcount > connerrthreshold at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        conn = 'r3'
        jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"connerr", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":"'+conn+'", "from":"'+socket.gethostname()+'"}'}
        print postData(jsondata)
        pass
    pass


def checkLocalOSInfo():
    try:
        osInfoStr = ''
        osInfoDict = {}
        print 'start to checkLocalOSInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('start to checkLocalOSInfo at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        import hashlib
        import psutil
        cpunum = psutil.cpu_count()
        mem = psutil.virtual_memory().total
        swap = psutil.swap_memory().total
        hostname = socket.gethostname()
        osInfoStr += str(cpunum)+str(mem)+str(swap)+hostname
        ipaddressstr = ''
        ifinfolist = []
        ifinfo = psutil.net_if_addrs()
        for key in ifinfo.keys():
            # print key
            # print ifinfo[key]
            if '127.0.0.1' == ifinfo[key][0].address:
                continue
            try:
                ifinfodict = {}
                ifinfodict['devicename'] = key
                ifinfodict['ipaddress'] = ifinfo[key][0].address
                ifinfodict['netmask'] = ifinfo[key][0].netmask
                ifinfodict['macaddress'] = ifinfo[key][1].address
                ipaddressstr += ifinfo[key][0].address+'|'
                ifinfolist.append(ifinfodict)
                osInfoStr += key+ifinfo[key][0].address+ifinfo[key][0].netmask+ifinfo[key][1].address
            except Exception,e:
                ifinfodict = {}
                ifinfodict['devicename'] = key
                ifinfodict['ipaddress'] = ifinfo[key][0].address
                # ifinfodict['netmask'] = ifinfo[key][0].netmask
                # ifinfodict['macaddress'] = ifinfo[key][1].address
                ipaddressstr += ifinfo[key][0].address+'|'
                ifinfolist.append(ifinfodict)
                osInfoStr += key+ifinfo[key][0].address#+ifinfo[key][0].netmask+ifinfo[key][1].address
            pass
        
        osInfoDict['cpunum'] = cpunum
        osInfoDict['mem'] = mem
        osInfoDict['swap'] = swap
        osInfoDict['hostname'] = hostname
        osInfoDict['ifinfo'] = ifinfolist
        osplatform = ''
        if sys.platform.startswith('linux'):
            osplatform = 'LINUX'
            pass
        else:
            osplatform = 'AIX'
        osInfoDict['osplatform'] = osplatform

        h = hashlib.md5(osInfoStr)
        hstr = h.hexdigest()

        filepath = '/tmp/osinfo.time'
        if not os.path.isfile(filepath): #如果不存在就返回False
            osinfossavehashfile = open(filepath, 'w+')
            osinfossavehashfile.close( )
        osinfossavehashfile = open(filepath, 'r+')
        osinfossavehash = osinfossavehashfile.read()
        if osinfossavehash == '':
            osinfossavehashfile.write(hstr)
            #post new osinfo
            encodedjson = json.dumps(osInfoDict)
            #print encodedjson
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"osinfo", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
            print postData(jsondata)

            sid = getConfig('SAP','sid').upper()
            localinstancelist = []
            localinstinfo = {}
            profilelist = getProfileList(sid)
            for p in profilelist:
                if hostname in p:
                    arr = p.split('_')
                    st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
                    localinstinfo['subappname'] = sid
                    localinstinfo['instid'] = arr[1]
                    localinstinfo['instno'] = arr[1][-2:]
                    instancetype = ''
                    if len(arr[1]) == 3:
                        instancetype = 'DI'
                    else:
                        instancetype = 'CI'
                    localinstinfo['instancetype'] = instancetype
                    localinstinfo['ostype'] = osplatform
                    localinstinfo['hostname'] = hostname
                    localinstinfo['ipaddress'] = ipaddressstr[0:-1]
                    localinstinfo['cpu'] = cpunum
                    localinstinfo['memory'] = mem #b
                    localinstancelist.append(localinstinfo)
                    localinstinfo = {}
                    pass
            encodedjson = json.dumps(localinstancelist)
            #print encodedjson
            jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"instinfo", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
            print postData(jsondata)
        else:
            if hstr != osinfossavehash:
                osinfossavehashfile.write(hstr)
                #post new osinfo
                encodedjson = json.dumps(osInfoDict)
                #print encodedjson
                jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"osinfo", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
                print postData(jsondata)
                sid = getConfig('SAP','sid').upper()
                localinstancelist = []
                localinstinfo = {}
                profilelist = getProfileList(sid)
                for p in profilelist:
                    if hostname in p:
                        arr = p.split('_')
                        st03instance = arr[2]+'_'+arr[0]+'_'+arr[1][-2:]
                        localinstinfo['subappname'] = sid
                        localinstinfo['instid'] = arr[1]
                        localinstinfo['instno'] = arr[1][-2:]
                        if len(arr[1]) == 3:
                            instancetype = 'DI'
                        else:
                            instancetype = 'CI'
                        localinstinfo['instancetype'] = instancetype
                        localinstinfo['ostype'] = osplatform
                        localinstinfo['hostname'] = hostname
                        localinstinfo['ipaddress'] = ipaddressstr[0:-1]
                        localinstinfo['cpu'] = cpunum
                        localinstinfo['memory'] = mem #b
                        localinstancelist.append(localinstinfo)
                        localinstinfo = {}
                        pass
                encodedjson = json.dumps(localinstancelist)
                #print encodedjson
                jsondata = {'postdata':'{"monitorid":"'+monitorid+'", "type":"instinfo", "datetime":"'+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+'", "data":'+encodedjson+', "from":"'+socket.gethostname()+'"}'}
                print postData(jsondata)
                pass
            else:
                pass
            pass
        osinfossavehashfile.close()
    except Exception,e:
        print e
        log.warning('checkLocalOSInfo error is '+str(e))
        log.warning(e)

class BasicCtrl(tornado.web.RequestHandler):
    def input(self, *args, **kwargs):
        return self.get_argument(*args, **kwargs)
    def asset(self, name, host='/static/', base='www', path='assets', vers=True):
        addr = os.path.join(path, name)

        if self.settings['debug']:
            orig = addr.replace('.min.', '.')
            if orig != addr and os.path.exists(os.path.join(self.settings['root_path'], base, orig)):
                addr = orig

        if vers:
            if isinstance(vers, bool):
                vers = tornado.web.StaticFileHandler.get_version({'static_path': ''},
                                                                 os.path.join(self.settings['root_path'], base,
                                                                              addr))
            if vers:
                return '%s?%s' % (os.path.join(host, addr), vers)
        return os.path.join(host, addr)

    pass


class Agent_IndexCtrl(BasicCtrl):
    def get(self, *args, **kwargs):
        self.render('Agent_IndexCtrl.html')
        pass

    pass

class Agent_LoginCtrl(BasicCtrl):
    def get(self, *args, **kwargs):
        pass

    pass

class Agent_LogoutCtrl(BasicCtrl):
    def get(self, *args, **kwargs):
        pass

    pass

class Agent_StatusCtrl(BasicCtrl):
    def get(self, *args, **kwargs):
        pass

    pass


class Agent_CallCtrl(BasicCtrl):
    def get(self, *args, **kwargs):
        pass
    def post(self, *args, **kwargs):
        print 'start to Agent_CallCtrl at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log.info('start to Agent_CallCtrl at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        token = u'8934e7d15453e97507ef794cf7b0519d'

        signature = self.input('signature', None)
        timestamp = self.input('timestamp', None)
        nonce = self.input('nonce', None)

        try:
            boolCheck = check_signature(token, signature, timestamp, nonce)
        except Exception,e:
            # 处理异常情况或忽略
            pass

        calltype = self.input('calltype', None)
        param = self.input('param', None)
        data = None
        if calltype == 'rfc':
            paramDict = json.load(param)
            rfcname = paramDict['rfcname']
            rfcparam = paramDict['rfcparam']

            global r3mainconn
            if r3mainconn == 0:
                print 'not main r3 conn and stop to Agent_CallCtrl at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log.info(
                    'not main r3 conn and stop to Agent_CallCtrl at ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                return

            sid = getConfig('SAP', 'sid')

            r3user = getConfig('r3', 'r3user')
            r3pwd = getConfig('r3', 'r3pwd')
            r3ashost = getConfig('r3', 'r3ashost')
            r3sysnr = getConfig('r3', 'r3sysnr')
            r3client = getConfig('r3', 'r3client')

            global r3connerrcount
            global r3conn
            if r3conn is None or not r3conn.alive:
                try:
                    r3conn = Connection(user=r3user, passwd=r3pwd, ashost=r3ashost, sysnr=r3sysnr, client=r3client)
                    r3connerrcount = 0
                except Exception, e:
                    r3connerrcount += 1
                    print e
                    print 'RFC connection is error'
                    log.warning(e)
                    log.warning('RFC connection is error')
                    return


            try:
                result = r3conn.call(rfcname,**rfcparam)
                r3conn.close()
                data =  json.dumps(result, cls=JsonCustomEncoder)
            except Exception, e:
                r3conn.close()
                log.warning(e)
                return ''

        if calltype == 'cmd':
            pass

        resp = {}
        resp['success'] = True
        resp['result'] = data
        self.write(resp)
        pass
    pass

def webService():
    url = [
        (r'/', Agent_IndexCtrl),
        (r'/login', Agent_LoginCtrl),
        (r'/logout', Agent_LogoutCtrl),
        (r'/status', Agent_StatusCtrl),
        (r'/call', Agent_CallCtrl),
    ]

    etc = {}
    etc['debug'] = False
    etc['error'] = False
    # etc['servs'] = 'AL/1.0.%s' % int(time.time())
    etc['root_path'] = sys.path[0]
    etc['login_url'] = '/login'
    etc['xsrf_cookies'] = True
    etc['cookie_secret'] = 'Yoursecretcookie'
    etc['template_path'] = os.path.join(etc['root_path'], 'view', '')
    etc['static_path'] = os.path.join(etc['root_path'], 'www', '')

    # tornado web
    svr = tornado.web.Application(handlers=url, **etc)
    define("port", default=59999, help="run on the given port", type=int)
    options.parse_command_line()
    print("Starting tornado web server on http://127.0.0.1:%s" % options.port)
    print("Quit the server with CONTROL-C")
    svr.listen(options.port, xheaders=True)
    tornado.ioloop.IOLoop.current().start()

    pass


# def monAgentServiceMain():
if __name__ == '__main__':
    threading.Thread(target=webService, name='webService').start()
    #main(sys.argv)
    #start()
    version = 1
    print 'start monitor agent v='+str(version)+' at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    '''
    logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='sappermonagent.log',
                filemode='w')
    '''

    loggerName = ''
    BASIC_LOG_PATH = './'
    filename = 'monagent.log'
    log = logging.getLogger(loggerName)
    #formatter = logging.Formatter('%(name)-12s %(asctime)s level-%(levelname)-8s thread-%(thread)-8d %(message)s')   # 每行日志的前缀设置
    formatter = logging.Formatter('%(asctime)s level-%(levelname)-8s thread-%(thread)-8d %(message)s')   # 每行日志的前缀设置
    #fileTimeHandler = TimedRotatingFileHandler(BASIC_LOG_PATH + filename, "D", 1, 30)
    fileTimeHandler = TimedRotatingFileHandler(BASIC_LOG_PATH + filename, when="midnight", backupCount=30)

    fileTimeHandler.suffix = "%Y%m%d"  #设置 切分后日志文件名的时间格式 默认 filename+"." + suffix 如果需要更改需要改logging 源码
    fileTimeHandler.setFormatter(formatter)
    logging.basicConfig(level = logging.DEBUG)
    fileTimeHandler.setFormatter(formatter)
    log.addHandler(fileTimeHandler)

    log.info('start monitor agent v='+str(version)+' at '+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    sid = getConfig('SAP','sid').upper()
    systype = getConfig('SAP','systype')

    rooturl = getConfig('XSAP','rooturl')
    posturl = getConfig('XSAP','posturl')
    updateurlconfig = getConfig('XSAP','updateurl')
    controlurlconfig = getConfig('XSAP','controlurl')
    monitorid = getConfig('XSAP','monitorid')
    proxy = getConfig('XSAP','proxy')
    montype = getConfig('XSAP','montype')
    updatetimeconfig = getConfig('XSAP','updatetime')

    '''
    fsexclude = getConfig('fs','exclude')

    database = sid
    dbtype = getConfig('db','dbtype')
    dbuser = getConfig('db','dbuser')
    dbpwd = getConfig('db','dbpwd')
    dbhost = getConfig('db','dbhost')
    dbport = getConfig('db','dbport')
    dbschema = getConfig('db','dbschema')
    dsn = "DATABASE="+sid+";HOSTNAME="+dbhost+";PORT="+str(dbport)+";PROTOCOL=TCPIP;UID="+dbuser+";PWD="+dbpwd+";"
    conn = ''

    r3user = getConfig('r3','r3user')
    r3pwd = getConfig('r3','r3pwd')
    r3ashost = getConfig('r3','r3ashost')
    r3sysnr = getConfig('r3','r3sysnr')
    r3client = getConfig('r3','r3client')

    osmonfrequency = getConfig('frequency','osmonfrequency') #min
    dbmonfrequency = getConfig('frequency','dbmonfrequency') #min
    instmonfrequency = getConfig('frequency','instmonfrequency') #min
    #sapjobmonfrequency = getConfig('frequency','sapjobmonfrequency') #min
    #sapdumpmonfrequency = getConfig('frequency','sapdumpmonfrequency') #min
    sapst03montime = getConfig('frequency','sapst03montime') #day
    dbbackupmontime = getConfig('frequency','dbbackupmontime') #day
    '''

    #getOption()
    #getConfig()
    options = OptionParser(usage='%prog ', description='XSAP SAP monitor agent')
    options.add_option('--damon', '-D', dest="damon", action="store_true", help="ask agent to run as Damon in background")
    opts, args = options.parse_args()

    #updatetime = '12:00'
    #updatetime = str(random.randint(0,23))+':'+str(random.randint(0,59))
    randomh = str(random.randint(0,23))
    randomm = str(random.randint(0,59))
    if len(randomh) == 1:
        randomh = '0'+randomh
    if len(randomm) == 1:
        randomm = '0'+randomm
    updatetime = randomh+':'+randomm
    if updatetimeconfig!='':
        updatetime = updatetimeconfig

    ###posturl is 1st parse condition because some servers have deployed agent base on it
    ###updateurl and others as optional parameter is 2nd parse condition, and then it is outdated
    ###rooturl as new and best parameter is final parse condition , and then it is best solution
    url = urlparse(posturl)
    updateurl = url.scheme+'://'+url.hostname+':'+str(url.port)+'/'+'api/updateagent'

    updateurlconfig = getConfig('XSAP','updateurl')
    if updateurlconfig!='':
        updateurl = updateurlconfig

    rooturlconfig = getConfig('XSAP','rooturl')
    if rooturlconfig!='':
        updateurl = rooturlconfig+'api/updateagent'

    programname = 'spdb2mon'
    osplatform = ''
    if sys.platform.startswith('linux'):
        osplatform = 'linux'
        pass
    else:
        osplatform = 'aix'
    identification=sid+'_'+socket.gethostname()+'_'+osplatform
    if proxy != '':
        schedule.every().day.at(updatetime).do(updateHelper,updateurl, version, programname, identification, proxy)
        pass
    else:
        schedule.every().day.at(updatetime).do(updateHelper,updateurl, version, programname, identification)
    #schedule.every(1).minutes.do(updateHelper,updateurl, version, programname, identification)

    dbmon = False
    sapmon = False
    osmon = False
    instmon = False

    #getOptionMore
    '''
    if opts.montype == 'all':
        #monitor all
        dbmon, sapmon, osmon, instmon = True
        pass
    else:
        if "db" in opts.montype:
            dbmon = True
        if "sap" in opts.montype:
            sapmon = True
        if "os" in opts.montype:
            osmon = True
        if "inst" in opts.montype:
            instmon = True
    '''

    schedule.every(1).minutes.do(sapInstController)
    schedule.every(1).minutes.do(cmdController)
    if systype == 'abap' or systype == 'both':
        schedule.every(1).minutes.do(rfcController)
    schedule.every(1).minutes.do(postConnerrMonData)

    #getOption
    if montype == 'all':
        #monitor all
        dbmon = True
        sapmon = True
        osmon = True
        instmon = True

        fsexclude = getConfig('fs','exclude')

        database = sid
        dbtype = getConfig('db','dbtype')
        dbuser = getConfig('db','dbuser')
        dbpwd = getConfig('db','dbpwd')
        dbhost = getConfig('db','dbhost')
        dbport = getConfig('db','dbport')
        dbschema = getConfig('db','dbschema')
        dsn = "DATABASE="+sid+";HOSTNAME="+dbhost+";PORT="+str(dbport)+";PROTOCOL=TCPIP;UID="+dbuser+";PWD="+dbpwd+";"
        conn = ''

        if systype == 'abap' or systype == 'both':
            r3user = getConfig('r3','r3user')
            r3pwd = getConfig('r3','r3pwd')
            r3ashost = getConfig('r3','r3ashost')
            r3sysnr = getConfig('r3','r3sysnr')
            r3client = getConfig('r3','r3client')
            sapst03montime = getConfig('frequency','sapst03montime') #day

        else:
            sapmon = False

        osmonfrequency = getConfig('frequency','osmonfrequency') #min
        dbmonfrequency = getConfig('frequency','dbmonfrequency') #min
        instmonfrequency = getConfig('frequency','instmonfrequency') #min
        #sapjobmonfrequency = getConfig('frequency','sapjobmonfrequency') #min
        #sapdumpmonfrequency = getConfig('frequency','sapdumpmonfrequency') #min

        dbbackupmontime = getConfig('frequency','dbbackupmontime') #day

        pass
    else:
        if "db" in montype:
            dbmon = True
            database = sid
            dbtype = getConfig('db','dbtype')
            dbuser = getConfig('db','dbuser')
            dbpwd = getConfig('db','dbpwd')
            dbhost = getConfig('db','dbhost')
            dbport = getConfig('db','dbport')
            dbschema = getConfig('db','dbschema')
            dsn = "DATABASE="+sid+";HOSTNAME="+dbhost+";PORT="+str(dbport)+";PROTOCOL=TCPIP;UID="+dbuser+";PWD="+dbpwd+";"
            conn = ''
            dbmonfrequency = getConfig('frequency','dbmonfrequency') #min
            dbbackupmontime = getConfig('frequency','dbbackupmontime') #day

        if "sap" in montype:
            if systype == 'abap' or systype == 'both':
                sapmon = True
                r3user = getConfig('r3','r3user')
                r3pwd = getConfig('r3','r3pwd')
                r3ashost = getConfig('r3','r3ashost')
                r3sysnr = getConfig('r3','r3sysnr')
                r3client = getConfig('r3','r3client')
                sapst03montime = getConfig('frequency','sapst03montime') #day
                instmonfrequency = getConfig('frequency','instmonfrequency') #min
            else:
                sapmon = False

        if "os" in montype:
            osmon = True
            fsexclude = getConfig('fs','exclude')
            osmonfrequency = getConfig('frequency','osmonfrequency') #min

        if "inst" in montype:
            instmon = True
            instmonfrequency = getConfig('frequency','instmonfrequency') #min

    if sys.platform.startswith('aix'):
        sapmon = False
        pass

    if dbmon:
        try:
            import ibm_db
            import ibm_db_dbi
        except ImportError:
            sys.exit("ibm_db not installed. Please install and import")

        if systype == 'abap' or systype == 'both':
            schedule.every(int(dbmonfrequency)).minutes.do(postDBMonData)
        else:
            schedule.every(int(dbmonfrequency)).minutes.do(postJavaDBMonData)

        schedule.every(int(dbmonfrequency)).minutes.do(postMutiBusySql)
        schedule.every().day.at(dbbackupmontime).do(postDbBackupMon)

    if osmon:
        try:
            import psutil
            import platform
            import socket
        except ImportError:
            sys.exit("psutil and platform not installed. Please install and import")
        schedule.every(int(osmonfrequency)).minutes.do(postOSMonData)

    import datetime as DatetimeCls
    checkLocalOSInfo()
    checkLocalOSDatetime = datetime.strptime(updatetime, '%H:%M')+DatetimeCls.timedelta(hours=1)
    schedule.every().day.at(checkLocalOSDatetime.strftime('%H:%M')).do(checkLocalOSInfo)

    if instmon:
        try:
            import socket
            import re
        except ImportError:
            sys.exit("socket and re not installed. Please install and import")
        schedule.every(int(instmonfrequency)).minutes.do(postInstMonData)

    if sapmon:
        try:
            import decimal
            from decimal import Decimal
            from pyrfc import Connection
            import re
        except ImportError:
            sys.exit("pyrfc, decimal and re not installed. Please install and import")

        if systype == 'abap' or systype == 'both':
            schedule.every().day.at(sapst03montime).do(postST03MonData)
            schedule.every(int(instmonfrequency)).minutes.do(postWPInfo)

        #schedule.every(int(dbmonfrequency)).minutes.do(postWPTotalActivity)
        #schedule.every(10).minutes.do(postWPTotalActivity)
        #schedule.every(2).minutes.do(postST03MonData)
        #schedule.every().day.at(sapst03montime).do(postST03MonData,conn,hostid,instance,datestr)
        #schedule.every().day.at(sapst03montime).do(postST03MonData)

    while True:
        schedule.run_pending()
        #schedule.run_continuously(600)
        import time
        time.sleep(1)

    print 'start Monitor agent ok'
