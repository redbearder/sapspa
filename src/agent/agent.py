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
from urllib.parse import urlparse

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
    import json

###################################################


def killProcessByName(programname):
    os.system("ps -C " + programname + " -o pid=|xargs kill -9")


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
    options = OptionParser(usage='%prog ',
                           description='XSAP SAP monitor agent')
    options.add_option('--sid',
                       '-s',
                       dest="sid",
                       default=sid,
                       help="SAP system SID")
    options.add_option('--dbuser',
                       '-u',
                       dest="dbuser",
                       default=dbuser,
                       help="Database access User for monitoring Database")
    options.add_option(
        '--dbpwd',
        '-p',
        dest="dbpwd",
        default=dbpwd,
        help="Database access User Password for monitoring Database")
    options.add_option('--posturl',
                       '-l',
                       dest="posturl",
                       default=posturl,
                       help="URL of posting monitor data to Centor collector")
    options.add_option('--monitorid',
                       '-i',
                       dest="monitorid",
                       default=monitorid,
                       help="ID for this system monitoring")
    options.add_option(
        '--montype',
        '-t',
        dest="montype",
        default='all',
        help=
        "Monitor type, default value is all, also can use 'db,sap,os,inst' as value instead of 'all' or part of this"
    )
    options.add_option(
        '--proxy',
        '-x',
        dest="proxy",
        default=proxy,
        help=
        "Agent proxy for accessing Center collector, like 'http://url:port/")
    options.add_option('--r3user',
                       '-U',
                       dest="r3user",
                       default=r3user,
                       help="R3 access user for SAP level monitor")
    options.add_option('--r3pwd',
                       '-P',
                       dest="r3pwd",
                       default=r3pwd,
                       help="R3 access user password for SAP level monitor")
    options.add_option('--r3ashost',
                       '-H',
                       dest="r3ashost",
                       default=r3ashost,
                       help="R3 access Hostname for SAP level monitor")
    options.add_option(
        '--r3sysnr',
        '-N',
        dest="r3sysnr",
        default=r3sysnr,
        help="R3 access System Instance Number for SAP level monitor")
    options.add_option('--r3client',
                       '-C',
                       dest="r3client",
                       default=r3client,
                       help="R3 access Client for SAP level monitor")
    options.add_option('--configfile',
                       '-f',
                       dest="configfile",
                       default=configfile,
                       help="ConfigFile path for SAP level monitor")
    options.add_option('--damon',
                       '-D',
                       dest="damon",
                       action="store_true",
                       help="ask agent to run as Damon in background")
    opts, args = options.parse_args()


def getOption():
    options = OptionParser(usage='%prog ',
                           description='XSAP SAP monitor agent')
    options.add_option('--damon',
                       '-D',
                       dest="damon",
                       action="store_true",
                       help="ask agent to run as Damon in background")
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
            r = requests.post(posturl,
                              data=jsondata,
                              timeout=10,
                              proxies=proxies)
            log.warning(r.text)
            if r.status_code == 200:
                if r.text == 'from_saprfcmonitor_0':
                    print 'from_saprfcmonitor_0 and r3mainconn = 0, not main r3 conn'
                    log.warning(
                        'from_saprfcmonitor_0 and r3mainconn = 0, not main r3 conn'
                    )
                    r3mainconn = 0

                if r.text == 'from_dbmonitor_0':
                    print 'from_dbmonitor_0 and dbmainconn = 0, not main db conn'
                    log.warning(
                        'from_dbmonitor_0 and dbmainconn = 0, not main db conn'
                    )
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
        except Exception as e:
            print(e)
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
        return json.dumps(result, cls=JsonCustomEncoder)
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''
    pass


def postDynamicRemoteFMCall(postParaJson):
    print('start to postDynamicRemoteFMCall at ' +
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    log.info('start to postDynamicRemoteFMCall at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postDynamicRemoteFMCall at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postDynamicRemoteFMCall at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
            r3conn = Connection(user=r3user,
                                passwd=r3pwd,
                                ashost=r3ashost,
                                sysnr=r3sysnr,
                                client=r3client)
            r3connerrcount = 0
        except Exception as e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    try:
        para = json.loads(postParaJson)
    except ValueError as e:
        return False
    instid = para['instid']
    fmName = para['fmName']
    fmParaArr = para['fmParaArr']
    for fmPara in fmParaArr:
        data = dynamicRemoteFMCall(r3conn, **fmPara)
        metadata = {}
        metadata['instid'] = instid
        metadata['fmName'] = fmName
        metadata['fmPara'] = fmPara
        jsondata = {
            'postdata':
            '{"monitorid":"' + monitorid +
            '", "type":"dynamicRemoteFMCall", "metadata":' +
            json.dumps(metadata, cls=JsonCustomEncoder) + ', "datetime":"' +
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
            data + '", "from":"' + socket.gethostname() + '"}'
        }
        print postData(jsondata)
    #print data
    pass


def getInstMonData():
    print 'start to getInstMonData at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to getInstMonData at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    hostname = socket.gethostname()
    sid = getConfig('SAP', 'sid')
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
            instname = arr[1]
            localinstancelist.append(instname)
            pass
    inststatuslist = []
    for instance in localinstancelist:
        cmd = 'tail -1 /usr/sap/' + sid + '/' + instance + '/work/available.log'
        status = os.popen(cmd).readline()
        if status.find('Available') == -1:
            print 'Stoped'
            log.info('Stoped')
            inststatus = {
                "inst": sid + "_" + instance + "_" + hostname,
                "status": "Stoped"
            }
        else:
            print 'Started'
            log.info('Started')
            inststatus = {
                "inst": sid + "_" + instance + "_" + hostname,
                "status": "Started"
            }
        inststatuslist.append(inststatus)
        pass
    return inststatuslist
    pass


def postInstMonData():
    data = getInstMonData()
    encodedjson = json.dumps(data)
    #print encodedjson
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid + '", "type":"inst", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
        encodedjson + ', "from":"' + socket.gethostname() + '"}'
    }

    print postData(jsondata)
    pass


#get OS profile list
def getProfileList(sid):
    #get profile path
    profilepath = '/sapmnt/' + sid + '/profile'
    profilelist = []
    try:
        list1 = os.listdir(profilepath)
        for l in list1:
            if '.' not in l and re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l):
                profilelist.append(l)
    except Exception as e:
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
            i = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
            serverinstancelist.append(i)
            pass
    return serverinstancelist


#CNV_MBT_ADM_WP_TOTAL_ACTIVITY RFC
def getWPTotalActivity(conn):
    try:
        result = conn.call('CNV_MBT_ADM_WP_TOTAL_ACTIVITY')
        conn.close()
        return json.dumps(result, cls=JsonCustomEncoder)
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''
    pass


def postWPTotalActivity():
    print 'start to postWPTotalActivity at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to postWPTotalActivity at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postWPTotalActivity at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postWPTotalActivity at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
            r3conn = Connection(user=r3user,
                                passwd=r3pwd,
                                ashost=r3ashost,
                                sysnr=r3sysnr,
                                client=r3client)
            r3connerrcount = 0
        except Exception as e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    data = getWPTotalActivity(r3conn)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid +
        '", "type":"wpTotalActivity", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' + data +
        ', "from":"' + socket.gethostname() + '"}'
    }
    print postData(jsondata)
    #print data
    pass


#TH_WPINFO RFC
def getWPInfoByServerName(conn, servername):
    try:
        result = conn.call('TH_WPINFO',
                           SRVNAME=servername,
                           WITH_CPU='00',
                           WITH_MTX_INFO=0,
                           MAX_ELEMS=0)
        conn.close()
        return json.dumps(result, cls=JsonCustomEncoder)
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''
    pass


def postWPInfo():
    print 'start to postWPInfo at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to postWPInfo at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postWPInfo at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postWPInfo at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
            r3conn = Connection(user=r3user,
                                passwd=r3pwd,
                                ashost=r3ashost,
                                sysnr=r3sysnr,
                                client=r3client)
            r3connerrcount = 0
        except Exception as e:
            r3connerrcount += 1
            print e
            print 'RFC connection is error'
            log.warning(e)
            log.warning('RFC connection is error')
            return

    instancelist = getServerInstanceList(sid)
    for i in instancelist:
        data = getWPInfoByServerName(r3conn, i)
        metadata = {}
        metadata['instancename'] = i
        jsondata = {
            'postdata':
            '{"monitorid":"' + monitorid + '", "type":"wpInfo", "metadata":' +
            json.dumps(metadata, cls=JsonCustomEncoder) + ', "datetime":"' +
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
            data + ', "from":"' + socket.gethostname() + '"}'
        }
        print postData(jsondata)
        pass

    #print data
    pass


#ST03 monitor statics data
def getSAPTuneSummaryStatistic(conn):
    try:
        result = conn.call('SAPTUNE_GET_SUMMARY_STATISTIC')
        conn.close()
        return json.dumps(result, cls=JsonCustomEncoder)
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''

    pass


def postSAPTuneSummaryStatistic(conn):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postSAPTuneSummaryStatistic at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info(
            'not main r3 conn and stop to postSAPTuneSummaryStatistic at ' +
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    data = getSAPTuneSummaryStatistic(conn)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid +
        '", "type":"wpTotalActivity", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' + data +
        ', "from":"' + socket.gethostname() + '"}'
    }
    print postData(jsondata)
    #print data
    pass


def getST03Summary(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    #result = conn.call('SAPWL_WORKLOAD_GET_SUMMARY', PERIODTYPE='D',HOSTID='PEKAX198',STARTDATE=datetime.strptime('20160302', '%Y%m%d'),INSTANCE='PEKAX198_CI2_01')
    try:
        result = conn.call('SAPWL_WORKLOAD_GET_SUMMARY',
                           PERIODTYPE=PERIODTYPE,
                           HOSTID=HOSTID,
                           STARTDATE=DATESTR,
                           INSTANCE=INSTANCE)
        conn.close()
        return json.dumps(result, cls=DecimalEncoder)
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''

    pass


def postST03Summary(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03Summary at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03Summary at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    #list /sapmnt/SID/profile and analyze to HOSTID, INSTANCE, DATESTR
    data = getST03Summary(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid +
        '", "type":"sapst03summary", "datetime":"' +
        datetime.strptime(DATESTR, '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S') +
        '", "instance":"' + INSTANCE + '", "data":' + data + ', "from":"' +
        socket.gethostname() + '"}'
    }
    print postData(jsondata)
    #print data
    pass


def getST03Statistic(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    try:
        result = conn.call('SAPWL_WORKLOAD_GET_STATISTIC',
                           PERIODTYPE=PERIODTYPE,
                           HOSTID=HOSTID,
                           STARTDATE=DATESTR,
                           INSTANCE=INSTANCE)
        conn.close()
        return json.dumps(result, cls=DecimalEncoder, encoding="ISO-8859-1")
    except Exception as e:
        conn.close()
        log.warning(e)
        return ''

    pass


def postST03Statistic(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE='D'):
    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03Statistic at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03Statistic at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    #list /sapmnt/SID/profile and analyze to HOSTID, INSTANCE, DATESTR
    data = getST03Statistic(conn, HOSTID, INSTANCE, DATESTR, PERIODTYPE)
    #print len(data)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid +
        '", "type":"sapst03statistic", "datetime":"' +
        datetime.strptime(DATESTR, '%Y%m%d').strftime('%Y-%m-%d %H:%M:%S') +
        '", "instance":"' + INSTANCE + '", "data":' + data + ', "from":"' +
        socket.gethostname() + '"}'
    }
    print postData(jsondata)
    #print data
    pass


def postST03MonData():
    print 'start to postST03MonData at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to postST03MonData at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global r3mainconn
    if r3mainconn == 0:
        print 'not main r3 conn and stop to postST03MonData at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main r3 conn and stop to postST03MonData at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
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
            r3conn = Connection(user=r3user,
                                passwd=r3pwd,
                                ashost=r3ashost,
                                sysnr=r3sysnr,
                                client=r3client)
            r3connerrcount = 0
        except Exception as e:
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
            i = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
            st03instancelist.append(i)
            pass
    for i in st03instancelist:
        hostid = i.split('_')[0]
        yesterday = datetime.now() + timedelta(days=-1)
        datestr = yesterday.strftime('%Y%m%d')
        instance = i
        try:
            postST03Summary(r3conn, hostid, instance, datestr)
            postST03Statistic(r3conn, hostid, instance, datestr)
        except Exception as e:
            log.warning(e)
            log.warning(instance +
                        ' data is not exist yet or RFC connection error')
            print instance + ' data is not exist yet or RFC connection error'


def getJobStatR(date, time):
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to getJobStatR at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to getJobStatR at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return

    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='R'"
    sql = "select * from " + dbschema + ".V_OP where STATUS='R'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_assoc(stmt)
        i = 0
        dbconnerrcount = 0
        while (row):
            result.append(row)
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception as e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass


def getJobStatF(date, time):
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='F'"
    sql = "select * from " + dbschema + ".V_OP where ENDDATE='" + date + "' and ENDTIME>'" + time + "' and STATUS='F'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_assoc(stmt)
        i = 0
        dbconnerrcount = 0
        while (row):
            result.append(row)
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception as e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass


def getJobStatA(date, time):
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from V_OP where STRTDATE='"+date+"' and STRTTIME>'"+time+"' and STATUS='A'"
    sql = "select * from " + dbschema + ".V_OP where ENDDATE='" + date + "' and ENDTIME>'" + time + "' and STATUS='A'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_assoc(stmt)
        i = 0
        dbconnerrcount = 0
        while (row):
            result.append(row)
            i += 1
            row = ibm_db.fetch_assoc(stmt)
        ibm_db.free_result(stmt)
        ibm_db.close(conn)
    except Exception as e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)
    return result
    pass


def getDumpNum(date):  #date format is 20160223
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    conn = ibm_db.connect(dsn, '', '', conn_options)
    sql = "select * from " + dbschema + ".SNAP where SEQNO='000' and DATUM='" + date + "'"
    stmt = ibm_db.exec_immediate(conn, sql)
    row = ibm_db.fetch_row(stmt)
    DUMPNUM = ibm_db.result(stmt, "DUMPNUM")
    ibm_db.close(conn)
    return DUMPNUM


def getTodayDumpNum():  #date format is 20160223
    date = datetime.now().strftime('%Y%m%d')
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    conn = ibm_db.connect(dsn, '', '', conn_options)
    sql = "select count(*) as DUMPNUM from " + dbschema + ".SNAP where SEQNO='000' and DATUM='" + date + "'"
    stmt = ibm_db.exec_immediate(conn, sql)
    row = ibm_db.fetch_row(stmt)
    DUMPNUM = ibm_db.result(stmt, "DUMPNUM")
    ibm_db.close(conn)
    return DUMPNUM
    pass


def getTodayDump():  #date format is 20160223
    filepath = '/tmp/querytodaydump.time'
    if not os.path.isfile(filepath):  #如果不存在就返回False
        savetimefile = open(filepath, 'w+')
        savetimefile.close()
    savetimefile = open(filepath, 'r')
    savetime = savetimefile.read()
    if savetime == '':
        lastdate = datetime.now().strftime('%Y%m%d')
        lasttime = '000000'
    else:
        thattime = time.strptime(savetime, "%Y-%m-%d %H:%M:%S.%f")
        lastdate = time.strftime('%Y%m%d', thattime)
        lasttime = time.strftime('%H%M%S', thattime)
        pass

    #date = datetime.now().strftime('%Y%m%d')
    conn_options = {ibm_db.SQL_ATTR_AUTOCOMMIT: ibm_db.SQL_AUTOCOMMIT_OFF}
    result = []
    #sql = "select * from "+dbschema+".SNAP where SEQNO='000' and DATUM='"+date+"'"
    sql = "select * from " + dbschema + ".SNAP where SEQNO='000' and DATUM='" + lastdate + "' and UZEIT>'" + lasttime + "'"

    global dbconnerrcount
    try:
        conn = ibm_db.connect(dsn, '', '', conn_options)
        stmt = ibm_db.exec_immediate(conn, sql)
        row = ibm_db.fetch_assoc(stmt)
        i = 0
        dbconnerrcount = 0
        while (row):
            result.append(row)
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
    except Exception as e:
        dbconnerrcount += 1
        print e
        log.warning(e)
        #ibm_db.close(conn)
        #raise _get_exception(inst)

    return result
    pass


def getNewJobStat():
    filepath = '/tmp/queryjobstat.time'
    if not os.path.isfile(filepath):  #如果不存在就返回False
        savetimefile = open(filepath, 'w+')
        savetimefile.close()
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
            lastdate = time.strftime('%Y%m%d', thattime)
            lasttime = time.strftime('%H%M%S', thattime)
            pass

        dataf = getJobStatF(lastdate, lasttime)
        datar = getJobStatR(lastdate, lasttime)
        dataa = getJobStatA(lastdate, lasttime)

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
    except Exception as e:
        print e
        log.warning(e)
        #raise e
        return data
    finally:
        savetimefile.close()


def postTodayDumpNum():
    data = getTodayDumpNum()
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid + '", "type":"sapdump", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
        str(data) + ', "from":"' + socket.gethostname() + '"}'
    }
    print postData(jsondata)
    pass


def postTodayDump():
    data = getTodayDump()
    encodedjson = json.dumps(data)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid + '", "type":"sapdump", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
        encodedjson + ', "from":"' + socket.gethostname() + '"}'
    }
    print postData(jsondata)
    pass


def postNewJobStat():
    data = getNewJobStat()
    encodedjson = json.dumps(data)
    #print encodedjson
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid + '", "type":"sapjob", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
        encodedjson + ', "from":"' + socket.gethostname() + '"}'
    }

    print postData(jsondata)
    pass


def postDbBackupMon():
    global dbmainconn
    if dbmainconn == 0:
        print 'not main db conn and stop to postDbBackupMon at ' + datetime.now(
        ).strftime('%Y-%m-%d %H:%M:%S')
        log.info('not main db conn and stop to postDbBackupMon at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        return
    data3 = getBackupLastday()
    encodedjson3 = json.dumps(data3, cls=DatetimeEncoder)
    jsondata = {
        'postdata':
        '{"monitorid":"' + monitorid +
        '", "type":"dbbackup", "dbtype":"db2", "datetime":"' +
        datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":{"backup":' +
        encodedjson3 + '}, "from":"' + socket.gethostname() + '"}'
    }

    print postData(jsondata)
    #print data1
    pass


### SAP and System control operation
def sapInstController():
    import subprocess
    print('start to sapInstController at ' +
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    log.info('start to sapInstController at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    hostname = socket.gethostname()
    sid = getConfig('SAP', 'sid').upper()
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
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
        except Exception as e:
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
            os.system('su - ' + sid.lower() + 'adm -c "cleanipc ' + nr +
                      ' remove"')
            print 'start instace'
            log.info('start instace')
            #os.system('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Start')
            (status, output) = commands.getstatusoutput(
                '/usr/sap/hostctrl/exe/sapcontrol -nr ' + nr +
                ' -function Start')
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"sapcontrolReturnData", "metadata":' +
                json.dumps(codedecode, cls=JsonCustomEncoder) +
                ', "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
                json.dumps(output, cls=JsonCustomEncoder) + '", "from":"' +
                socket.gethostname() + '"}'
            }
            print(postData(jsondata))
            pass
        if code == '2':
            #stop
            print 'stop instace'
            log.info('stop instace')
            #os.system('/usr/sap/hostctrl/exe/sapcontrol -nr '+nr+' -function Stop')
            (status, output) = commands.getstatusoutput(
                '/usr/sap/hostctrl/exe/sapcontrol -nr ' + nr +
                ' -function Stop')
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"sapcontrolReturnData", "metadata":' +
                json.dumps(codedecode, cls=JsonCustomEncoder) +
                ', "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
                json.dumps(output, cls=JsonCustomEncoder) + '", "from":"' +
                socket.gethostname() + '"}'
            }
            print postData(jsondata)
            pass
        pass
    pass


def cmdController():
    '''
    
    :return: 
    '''
    print 'start to cmdController at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to cmdController at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    import commands
    hostname = socket.gethostname()
    sid = getConfig('SAP', 'sid').upper()
    localinstancelist = []
    profilelist = getProfileList(sid)
    for p in profilelist:
        if hostname in p:
            arr = p.split('_')
            st03instance = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
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
        except Exception as e:
            continue
        nr = instance[-2:]
        cmd = cmddict['cmd']
        instid = cmddict['instid']
        jsonEncode = cmddict['jsonEncode']
        #do cmd and post return
        (status, output) = commands.getstatusoutput(str(cmd))
        print 'start to postCMDReturnData at ' + datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')
        log.info('start to postCMDReturnData at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        metadata = {}
        metadata['instid'] = instid
        metadata['cmd'] = cmd
        metadata['status'] = status
        if jsonEncode:
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"cmdReturnData", "metadata":' +
                json.dumps(metadata, cls=JsonCustomEncoder) +
                ', "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
                json.dumps(output, cls=JsonCustomEncoder) + ', "from":"' +
                socket.gethostname() + '"}'
            }
            print postData(jsondata)
        else:
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"cmdReturnData", "metadata":' +
                json.dumps(metadata, cls=JsonCustomEncoder) +
                ', "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
                output + '", "from":"' + socket.gethostname() + '"}'
            }
            if getConfig('XSAP', 'debug'):
                log.info(jsondata)
            print postData(jsondata)

        pass
    pass


def createScheduler():
    #schedule.every().hour.do(job)
    schedule.every().day.at(sapst03montime).do(postST03MonData)
    #schedule.every().monday.do(job)
    #schedule.every().wednesday.at("13:15").do(job)


def getRootUrlConfig(configfile='spdb2mon.cfg'):
    try:
        config = ConfigObj(configfile)
        sec = config['XSAP']
        v = sec['rooturl']
        return v
    except Exception as e:
        return 'http://api.sapper.cn/'


def getConfig(section, key, configfile='spdb2mon.cfg'):
    try:
        config = ConfigObj(configfile)
        sec = config[section]
        v = sec[key]
        return v
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
    except Exception as e:
        if key == 'rooturl':
            return 'http://api.sapper.cn/'
        if key == 'posturl':
            return getRootUrlConfig() + 'mon/collect'
        if key == 'controlurl':
            return ''
        if key == 'commandurl':
            return ''
        if key == 'rfcurl':
            return ''
        if key == 'updatetime':
            return ''
        if key == 'updateurl':
            return ''
        if key == 'debug':
            return 0
        if key == 'systype':
            return 'abap'
        print 'Configuration ' + str(e) + ' is missing'
        print 'please fulfill Configuration in spdb2mon.cfg file with Same Path'
        log.warning(e)
        log.warning('Configuration ' + str(e) + ' is missing')
        log.warning(
            'please fulfill Configuration in spdb2mon.cfg file with Same Path')
        sys.exit(0)
    pass


def updateHelper(updateurl, version, programname, identification, proxy=None):
    #start another process to check
    #if new update, terminate mon agent process
    #download and uncompress update.zip in current DIR
    #then sys.exit(0)
    #start mon agent process background
    #exec updatehelper
    print('check update')
    log.info('check update')
    if proxy:
        os.system('./updatehelper --url=' + updateurl + ' --version=' +
                  str(version) + ' --program=' + programname +
                  ' --identification=' + identification + ' --proxy=' + proxy +
                  ' >>updatehelper.log &')
        pass
    else:
        os.system('./updatehelper --url=' + updateurl + ' --version=' +
                  str(version) + ' --program=' + programname +
                  ' --identification=' + identification +
                  ' >>updatehelper.log &')
        pass
    pass


def createDaemon():
    #Funzione che crea un demone per eseguire un determinato programma

    import os

    # create - fork 1
    try:
        if os.fork() > 0:
            os._exit(0)  # exit father
    except OSError as error:
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
    except OSError as error:
        print 'fork #2 failed: %d (%s)' % (error.errno, error.strerror)
        os._exit(1)

    #funzioneDemo() # function demo


def postConnerrMonData():
    print 'start to postConnerrMonData at ' + datetime.now().strftime(
        '%Y-%m-%d %H:%M:%S')
    log.info('start to postConnerrMonData at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    global dbconnerrcount
    global r3connerrcount
    connerrthreshold = 10
    if dbconnerrcount > connerrthreshold:
        log.warning('connerr is dbconnerrcount > connerrthreshold at ' +
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        conn = 'db'
        jsondata = {
            'postdata':
            '{"monitorid":"' + monitorid +
            '", "type":"connerr", "datetime":"' +
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
            conn + '", "from":"' + socket.gethostname() + '"}'
        }
        print postData(jsondata)
        pass
    if r3connerrcount > connerrthreshold:
        log.warning('connerr is r3connerrcount > connerrthreshold at ' +
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        conn = 'r3'
        jsondata = {
            'postdata':
            '{"monitorid":"' + monitorid +
            '", "type":"connerr", "datetime":"' +
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":"' +
            conn + '", "from":"' + socket.gethostname() + '"}'
        }
        print postData(jsondata)
        pass
    pass


def checkLocalOSInfo():
    try:
        osInfoStr = ''
        osInfoDict = {}
        log.info('start to checkLocalOSInfo at ' +
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        import hashlib
        import psutil
        cpunum = psutil.cpu_count()
        mem = psutil.virtual_memory().total
        swap = psutil.swap_memory().total
        hostname = socket.gethostname()
        osInfoStr += str(cpunum) + str(mem) + str(swap) + hostname
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
                ipaddressstr += ifinfo[key][0].address + '|'
                ifinfolist.append(ifinfodict)
                osInfoStr += key + ifinfo[key][0].address + ifinfo[key][
                    0].netmask + ifinfo[key][1].address
            except Exception as e:
                ifinfodict = {}
                ifinfodict['devicename'] = key
                ifinfodict['ipaddress'] = ifinfo[key][0].address
                # ifinfodict['netmask'] = ifinfo[key][0].netmask
                # ifinfodict['macaddress'] = ifinfo[key][1].address
                ipaddressstr += ifinfo[key][0].address + '|'
                ifinfolist.append(ifinfodict)
                osInfoStr += key + ifinfo[key][
                    0].address  #+ifinfo[key][0].netmask+ifinfo[key][1].address
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
        if not os.path.isfile(filepath):  #如果不存在就返回False
            osinfossavehashfile = open(filepath, 'w+')
            osinfossavehashfile.close()
        osinfossavehashfile = open(filepath, 'r+')
        osinfossavehash = osinfossavehashfile.read()
        if osinfossavehash == '':
            osinfossavehashfile.write(hstr)
            #post new osinfo
            encodedjson = json.dumps(osInfoDict)
            #print encodedjson
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"osinfo", "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
                encodedjson + ', "from":"' + socket.gethostname() + '"}'
            }
            print postData(jsondata)

            sid = getConfig('SAP', 'sid').upper()
            localinstancelist = []
            localinstinfo = {}
            profilelist = getProfileList(sid)
            for p in profilelist:
                if hostname in p:
                    arr = p.split('_')
                    st03instance = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
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
                    localinstinfo['memory'] = mem  #b
                    localinstancelist.append(localinstinfo)
                    localinstinfo = {}
                    pass
            encodedjson = json.dumps(localinstancelist)
            #print encodedjson
            jsondata = {
                'postdata':
                '{"monitorid":"' + monitorid +
                '", "type":"instinfo", "datetime":"' +
                datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '", "data":' +
                encodedjson + ', "from":"' + socket.gethostname() + '"}'
            }
            print postData(jsondata)
        else:
            if hstr != osinfossavehash:
                osinfossavehashfile.write(hstr)
                #post new osinfo
                encodedjson = json.dumps(osInfoDict)
                #print encodedjson
                jsondata = {
                    'postdata':
                    '{"monitorid":"' + monitorid +
                    '", "type":"osinfo", "datetime":"' +
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S') +
                    '", "data":' + encodedjson + ', "from":"' +
                    socket.gethostname() + '"}'
                }
                print postData(jsondata)
                sid = getConfig('SAP', 'sid').upper()
                localinstancelist = []
                localinstinfo = {}
                profilelist = getProfileList(sid)
                for p in profilelist:
                    if hostname in p:
                        arr = p.split('_')
                        st03instance = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
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
                        localinstinfo['memory'] = mem  #b
                        localinstancelist.append(localinstinfo)
                        localinstinfo = {}
                        pass
                encodedjson = json.dumps(localinstancelist)
                #print encodedjson
                jsondata = {
                    'postdata':
                    '{"monitorid":"' + monitorid +
                    '", "type":"instinfo", "datetime":"' +
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S') +
                    '", "data":' + encodedjson + ', "from":"' +
                    socket.gethostname() + '"}'
                }
                print postData(jsondata)
                pass
            else:
                pass
            pass
        osinfossavehashfile.close()
    except Exception as e:
        print(e)
        log.warning('checkLocalOSInfo error is ' + str(e))
        log.warning(e)


if __name__ == '__main__':
    version = 1
    print('start monitor agent v=' + str(version) + ' at ' +
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    loggerName = ''
    BASIC_LOG_PATH = './'
    filename = 'monagent.log'
    log = logging.getLogger(loggerName)
    formatter = logging.Formatter(
        '%(asctime)s level-%(levelname)-8s thread-%(thread)-8d %(message)s')
    fileTimeHandler = TimedRotatingFileHandler(BASIC_LOG_PATH + filename,
                                               when="midnight",
                                               backupCount=30)

    fileTimeHandler.suffix = "%Y%m%d"
    fileTimeHandler.setFormatter(formatter)
    logging.basicConfig(level=logging.DEBUG)
    fileTimeHandler.setFormatter(formatter)
    log.addHandler(fileTimeHandler)

    log.info('start monitor agent v=' + str(version) + ' at ' +
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    sid = getConfig('SAP', 'sid').upper()
    systype = getConfig('SAP', 'systype')

    rooturl = getConfig('XSAP', 'rooturl')
    posturl = getConfig('XSAP', 'posturl')
    updateurlconfig = getConfig('XSAP', 'updateurl')
    controlurlconfig = getConfig('XSAP', 'controlurl')
    monitorid = getConfig('XSAP', 'monitorid')
    proxy = getConfig('XSAP', 'proxy')
    montype = getConfig('XSAP', 'montype')
    updatetimeconfig = getConfig('XSAP', 'updatetime')

    options = OptionParser(usage='%prog ',
                           description='XSAP SAP monitor agent')
    options.add_option('--damon',
                       '-D',
                       dest="damon",
                       action="store_true",
                       help="ask agent to run as Damon in background")
    opts, args = options.parse_args()

    randomh = str(random.randint(0, 23))
    randomm = str(random.randint(0, 59))
    if len(randomh) == 1:
        randomh = '0' + randomh
    if len(randomm) == 1:
        randomm = '0' + randomm
    updatetime = randomh + ':' + randomm
    if updatetimeconfig != '':
        updatetime = updatetimeconfig

    ###posturl is 1st parse condition because some servers have deployed agent base on it
    ###updateurl and others as optional parameter is 2nd parse condition, and then it is outdated
    ###rooturl as new and best parameter is final parse condition , and then it is best solution
    url = urlparse(posturl)
    updateurl = url.scheme + '://' + url.hostname + ':' + str(
        url.port) + '/' + 'api/updateagent'

    updateurlconfig = getConfig('XSAP', 'updateurl')
    if updateurlconfig != '':
        updateurl = updateurlconfig

    rooturlconfig = getConfig('XSAP', 'rooturl')
    if rooturlconfig != '':
        updateurl = rooturlconfig + 'api/updateagent'

    programname = 'spdb2mon'
    osplatform = ''
    if sys.platform.startswith('linux'):
        osplatform = 'linux'
        pass
    else:
        osplatform = 'aix'
    identification = sid + '_' + socket.gethostname() + '_' + osplatform
    if proxy != '':
        schedule.every().day.at(updatetime).do(updateHelper, updateurl,
                                               version, programname,
                                               identification, proxy)
        pass
    else:
        schedule.every().day.at(updatetime).do(updateHelper, updateurl,
                                               version, programname,
                                               identification)
    #schedule.every(1).minutes.do(updateHelper,updateurl, version, programname, identification)

    dbmon = False
    sapmon = False
    osmon = False
    instmon = False

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

        fsexclude = getConfig('fs', 'exclude')

        database = sid
        dbtype = getConfig('db', 'dbtype')
        dbuser = getConfig('db', 'dbuser')
        dbpwd = getConfig('db', 'dbpwd')
        dbhost = getConfig('db', 'dbhost')
        dbport = getConfig('db', 'dbport')
        dbschema = getConfig('db', 'dbschema')
        dsn = "DATABASE=" + sid + ";HOSTNAME=" + dbhost + ";PORT=" + str(
            dbport) + ";PROTOCOL=TCPIP;UID=" + dbuser + ";PWD=" + dbpwd + ";"
        conn = ''

        if systype == 'abap' or systype == 'both':
            r3user = getConfig('r3', 'r3user')
            r3pwd = getConfig('r3', 'r3pwd')
            r3ashost = getConfig('r3', 'r3ashost')
            r3sysnr = getConfig('r3', 'r3sysnr')
            r3client = getConfig('r3', 'r3client')
            sapst03montime = getConfig('frequency', 'sapst03montime')  #day

        else:
            sapmon = False

        osmonfrequency = getConfig('frequency', 'osmonfrequency')  #min
        dbmonfrequency = getConfig('frequency', 'dbmonfrequency')  #min
        instmonfrequency = getConfig('frequency', 'instmonfrequency')  #min
        #sapjobmonfrequency = getConfig('frequency','sapjobmonfrequency') #min
        #sapdumpmonfrequency = getConfig('frequency','sapdumpmonfrequency') #min

        dbbackupmontime = getConfig('frequency', 'dbbackupmontime')  #day

        pass
    else:
        if "db" in montype:
            dbmon = True
            database = sid
            dbtype = getConfig('db', 'dbtype')
            dbuser = getConfig('db', 'dbuser')
            dbpwd = getConfig('db', 'dbpwd')
            dbhost = getConfig('db', 'dbhost')
            dbport = getConfig('db', 'dbport')
            dbschema = getConfig('db', 'dbschema')
            dsn = "DATABASE=" + sid + ";HOSTNAME=" + dbhost + ";PORT=" + str(
                dbport
            ) + ";PROTOCOL=TCPIP;UID=" + dbuser + ";PWD=" + dbpwd + ";"
            conn = ''
            dbmonfrequency = getConfig('frequency', 'dbmonfrequency')  #min
            dbbackupmontime = getConfig('frequency', 'dbbackupmontime')  #day

        if "sap" in montype:
            if systype == 'abap' or systype == 'both':
                sapmon = True
                r3user = getConfig('r3', 'r3user')
                r3pwd = getConfig('r3', 'r3pwd')
                r3ashost = getConfig('r3', 'r3ashost')
                r3sysnr = getConfig('r3', 'r3sysnr')
                r3client = getConfig('r3', 'r3client')
                sapst03montime = getConfig('frequency', 'sapst03montime')  #day
                instmonfrequency = getConfig('frequency',
                                             'instmonfrequency')  #min
            else:
                sapmon = False

        if "os" in montype:
            osmon = True
            fsexclude = getConfig('fs', 'exclude')
            osmonfrequency = getConfig('frequency', 'osmonfrequency')  #min

        if "inst" in montype:
            instmon = True
            instmonfrequency = getConfig('frequency', 'instmonfrequency')  #min

    if sys.platform.startswith('aix'):
        sapmon = False
        pass

    import datetime as DatetimeCls
    checkLocalOSInfo()
    checkLocalOSDatetime = datetime.strptime(
        updatetime, '%H:%M') + DatetimeCls.timedelta(hours=1)
    schedule.every().day.at(
        checkLocalOSDatetime.strftime('%H:%M')).do(checkLocalOSInfo)

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
            sys.exit(
                "pyrfc, decimal and re not installed. Please install and import"
            )

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

    print('start Monitor agent ok')
