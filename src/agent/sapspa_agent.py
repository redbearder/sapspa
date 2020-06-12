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
from prometheus_client.core import REGISTRY, CounterMetricFamily, GaugeHistogramMetricFamily, GaugeMetricFamily, HistogramMetricFamily, InfoMetricFamily, SummaryMetricFamily, StateSetMetricFamily
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from datetime import date, time, timedelta, datetime
import random
import time
import requests
import schedule
from configobj import ConfigObj
from optparse import OptionParser
from pyrfc import Connection
from decimal import Decimal
import consul
import yaml
import shlex, subprocess
from elasticsearch import Elasticsearch


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


def get_host_info():
    cpu = psutil.cpu_count()
    mem = psutil.virtual_memory().total
    swap = psutil.swap_memory().total
    hostname = socket.gethostname()
    ipaddress: List[Dict] = []
    ifinfo = psutil.net_if_addrs()
    for key in ifinfo.keys():
        if '127.0.0.1' == ifinfo[key][0].address:
            continue
        ifinfodict = {}
        ifinfodict['device'] = key
        ifinfodict['ip'] = ifinfo[key][0].address
        ipaddress.append(ifinfodict)

    return {
        "cpu": cpu,
        "mem": mem,
        "swap": swap,
        "hostname": hostname,
        "ip": ipaddress
    }


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


def get_instance_list_by_sid(sid):
    instance: List[Dict] = []
    profilepath = '/sapmnt/' + sid + '/profile'
    list1 = os.listdir(profilepath)
    for l in list1:
        m = re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l)
        if m and m.group() == l:
            p = {}
            p['profile'] = l
            arr = l.split('_')
            p['sysnr'] = arr[1][-2:]
            p['host'] = arr[2]
            p['sid'] = arr[0]
            i = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
            p['servername'] = i
            if 'ASCS' not in l:
                p['type'] = 'DIALOG'
            else:
                # ASCS
                p['type'] = 'ASCS'
            instance.append(p)
    return instance


def get_hdb_list_by_sid(sid):
    instance: List[Dict] = []
    profilepath = '/usr/sap/' + sid + '/SYS/profile'
    list1 = os.listdir(profilepath)
    for l in list1:
        m = re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l)
        if m and m.group() == l:
            p = {}
            p['profile'] = l
            arr = l.split('_')
            p['sysnr'] = arr[1][-2:]
            p['host'] = arr[2]
            p['sid'] = arr[0]
            i = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
            p['servername'] = i
            p['type'] = 'HDB'
            instance.append(p)
    return instance


def get_instance_servername_list_by_sid(sid):
    diaServernameList: List[Dict] = []
    profilepath = '/sapmnt/' + sid + '/profile'
    list1 = os.listdir(profilepath)
    for l in list1:
        m = re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l)
        if m and m.group() == l:
            p = {}
            p['profile'] = l
            if 'ASCS' not in l:
                p['type'] = 'DIALOG'
                arr = l.split('_')
                i = arr[2] + '_' + arr[0] + '_' + arr[1][-2:]
                p['servername'] = i
                diaServernameList.append(p)
                pass
    return diaServernameList


class R3rfcconn(object):
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

    def get_table_data(
            self,
            tablename: str,
            offset: int = 0,
            limit: int = 0,
            options: List = [],
            fields: List = [],
    ):
        read_table_fm = 'RFC_READ_TABLE'
        kwparam = {}
        kwparam['QUERY_TABLE'] = tablename
        kwparam['ROWSKIPS'] = offset
        kwparam['ROWCOUNT'] = limit
        kwparam['OPTIONS'] = options
        kwparam['FIELDS'] = fields
        result = self.conn.call(read_table_fm, **kwparam)
        return result

    def get_rfc_data(self, fm: str, **kwparam: dict):
        result = self.conn.call(fm, **kwparam)
        # return json.dumps(result, cls=JsonCustomEncoder)
        return result

    def get_server_wp_list(self, servername):
        '''
        get workprocess list and info by servername
        :param servername: s4ides1_DM0_00
        :return: 
        '''
        kwparam = {}
        kwparam['SRVNAME'] = servername
        kwparam['WITH_CPU'] = b'00'
        kwparam['WITH_MTX_INFO'] = 0
        kwparam['MAX_ELEMS'] = 0
        return self.get_rfc_data('TH_WPINFO', **kwparam)['WPLIST']

    def get_user_list(self):
        '''
        get SID overall wp info
        :return: 
        '''
        kwparam = {}
        return self.get_rfc_data('TH_USER_LIST', **kwparam)['USRLIST']

    def get_bkjob_status_count(self):
        '''
        tables: TBTCP,TBTCO and TBTCS, views: V_OP
        get per 15s by promethues define scrawl
        The statuses have the following meanings:

            Scheduled: not yet been released to run. P
            Released: released to run. S
            Ready: start date and time have come: awaiting execution.
            Active: currently running. R
            After a system failure, can indicate that a job was interrupted by the failure and must be manually restarted.
            
            Finished: successfully completed. F
            Aborted: not successfully completed. A
            
        :param servername: 
        :return: 
        '''

        job_finish = self.get_table_data(
            'V_OP',
            options=[
                f"STATUS EQ 'F' AND ENDDATE EQ '{date.today()}' AND ENDTIME GT '{(datetime.now()-timedelta(seconds=15)).strftime('%H%M%S')}'"
            ],
            fields=[
                'JOBNAME', 'STRTDATE', 'STRTTIME', 'ENDDATE', 'ENDTIME',
                'PRDMINS', 'PRDHOURS', 'STATUS'
            ])
        job_running = self.get_table_data('V_OP',
                                          options=[f"STATUS EQ 'R'"],
                                          fields=[
                                              'JOBNAME', 'STRTDATE',
                                              'STRTTIME', 'ENDDATE', 'ENDTIME',
                                              'PRDMINS', 'PRDHOURS', 'STATUS'
                                          ])
        job_cancel = self.get_table_data(
            'V_OP',
            options=[
                f"STATUS EQ 'A' AND ENDDATE EQ '{date.today()}' AND ENDTIME GT '{(datetime.now()-timedelta(seconds=15)).strftime('%H%M%S')}'"
            ],
            fields=[
                'JOBNAME', 'STRTDATE', 'STRTTIME', 'ENDDATE', 'ENDTIME',
                'PRDMINS', 'PRDHOURS', 'STATUS'
            ])
        return {
            "finish": len(job_finish['DATA']),
            "running": len(job_running['DATA']),
            "cancel": len(job_cancel['DATA'])
        }

    def get_dump_list(self):
        # date.today() - timedelta(1), DATE_TO = date.today(), TIME_FROM = '000000', TIME_TO = '235959')
        kwparam = {}
        kwparam['DATE_FROM'] = date.today()
        kwparam['TIME_FROM'] = b'000000'
        kwparam['DATE_TO'] = date.today()
        kwparam['TIME_TO'] = b'235959'
        try:
            return self.get_rfc_data('/SDF/GET_DUMP_LOG',
                                     **kwparam)['ET_E2E_LOG']
        except:
            return []

    def get_rfcresource_list(self, servername):
        '''
        need confirm
        :param servername: 
        :return: 
        '''
        kwparam = {}
        return self.get_rfc_data('RFC_SERVER_GROUP_RESOURCES', **kwparam)

    def get_transport_list(self):
        tablename = 'E070'
        return self.get_table_data(tablename)

    def get_st02_data(self):
        kwparam = {}
        st02data = self.get_rfc_data('SAPTUNE_GET_SUMMARY_STATISTIC')
        del st02data['TABLE_QUALITIES']
        del st02data['TABLE_STATISTIC']
        del st02data['TABLE_STATISTIC_64']
        del st02data['CURSOR_CACHE_INFO']
        del st02data['MODE_MEMORY_HISTORY']
        del st02data['INTERNAL_EXTERNAL_MODES_MEMORY']
        del st02data['BUFFER_STATISTIC_64']
        st02data_json = json.dumps(st02data, cls=DecimalEncoder)
        return json.loads(st02data_json)

    def get_st03_data_summary(self):
        kwparam = {}
        kwparam['READ_START_DATE'] = date.today()
        kwparam['READ_END_DATE'] = date.today()
        kwparam['READ_START_TIME'] = (datetime.now() -
                                      timedelta(seconds=60)).strftime('%H%M%S')
        kwparam['READ_END_TIME'] = (datetime.now() -
                                    timedelta(seconds=0)).strftime('%H%M%S')
        st03datadetail = self.get_rfc_data('SAPWL_SNAPSHOT_FROM_REMOTE_SYS',
                                           **kwparam)
        st03datadetail_json = json.dumps(st03datadetail['SUMMARY'],
                                         cls=DecimalEncoder)
        return json.loads(st03datadetail_json)

    def close(self):
        self.conn.close()


# Create my app
app = Flask(__name__)
app.config['DEBUG'] = True


@app.route('/', methods=['GET'])
def index():
    return 'This is a wrong Index Page'


@app.route('/api/hosts', methods=['GET'])
def hosts():
    return 'current hosts info'


@app.route('/api/apps', methods=['GET'])
def subapps_info():
    '''
    here app means subapp
    :return: all subapp infomation includes instances info
    '''
    return 'current apps, subapps, instances, profiles info'


@app.route('/api/apps/<string:sid>', methods=['GET'])
def subapp_info(sid):
    '''
    all subapp infomation includes instances info
    :param sid: SAP SID 
    :return: sid subapp infomation includes instances info
    '''
    return 'current subapp_info info'


@app.route('/api/apps/<string:sid>/instances', methods=['GET'])
def subapp_instances(sid):
    return 'current subapp_instances info'


@app.route('/api/apps/<string:sid>/instances/<string:instanceid>',
           methods=['GET'])
def subapp_instance_info(sid, instanceid):
    return 'current subapp_instances info'


@app.route('/api/apps/<string:sid>/instances/<string:instanceid>/status',
           methods=['POST'])
def subapp_instance_start(sid, instanceid):
    sysnr = instanceid[-2:]
    instance_start_cmd = f'su - {sid.lower()}adm -c "sapcontrol -nr {sysnr} -function StartSystem"'
    instance_start_cmd_args = shlex.split(instance_start_cmd)
    sp = subprocess.run(instance_start_cmd_args, capture_output=True)
    output = sp.stdout.decode('utf-8')
    return output


@app.route('/api/apps/<string:sid>/instances/<string:instanceid>/status',
           methods=['DELETE'])
def subapp_instance_stop(sid, instanceid):
    sysnr = instanceid[-2:]
    instance_stop_cmd = f'su - {sid.lower()}adm -c "sapcontrol -nr {sysnr} -function StopSystem"'
    instance_stop_cmd_args = shlex.split(instance_stop_cmd)
    sp = subprocess.run(instance_stop_cmd_args, capture_output=True)
    output = sp.stdout.decode('utf-8')
    return output


@app.route('/api/apps/<string:sid>/instances/<string:instanceid>/status',
           methods=['GET'])
def subapp_instance_status(sid, instanceid):
    sysnr = instanceid[-2:]
    instance_check_cmd = f'su - {sid.lower()}adm -c "sapcontrol -nr {sysnr} -function GetProcessList"'
    instance_check_cmd_args = shlex.split(instance_check_cmd)
    sp = subprocess.run(instance_check_cmd_args, capture_output=True)
    output = sp.stdout.decode('utf-8')
    if 'Red' in output or 'GRAY' in output:
        return '0'
    else:
        return '1'


class SAPCollector(object):
    def __init__(self):
        pass

    def collect(self):
        # get SID list from os dir
        sidList = get_sid_list()
        for sid in sidList:
            c = consul.Consul(host=os.environ.get('CONSUL_HOST') if
                              os.environ.get('CONSUL_HOST') else '127.0.0.1',
                              port=23345,
                              scheme='http')
            kvid, kvv = c.kv.get(sid + '_login')
            if kvv:
                # get SID login info from consul
                kvvDict = json.loads(kvv['Value'])
                conn = None

                for instance in get_instance_list_by_sid(sid):
                    if not conn and instance['type'] == 'DIALOG':
                        conn = R3rfcconn(r3ashost='127.0.0.1',
                                         r3sysnr=instance['sysnr'],
                                         r3client=kvvDict['r3client'],
                                         r3user=kvvDict['r3user'],
                                         r3pwd=kvvDict['r3pwd'])

                    instance_check_cmd = f'su - {sid.lower()}adm -c "sapcontrol -nr {instance["sysnr"]} -function GetProcessList"'
                    instance_check_cmd_args = shlex.split(instance_check_cmd)
                    sp = subprocess.run(instance_check_cmd_args,
                                        capture_output=True)
                    output = sp.stdout.decode('utf-8')
                    outputlines = output.splitlines()
                    if 'Red' in output:
                        g_instancestatus = StateSetMetricFamily(
                            "InstanceStatus",
                            'Instance Status Check in SID',
                            labels=['SID', 'Instance'])
                        g_instancestatus.add_metric([sid, instance["profile"]],
                                                    {'status': False})
                        yield g_instancestatus
                    else:
                        g_instancestatus = StateSetMetricFamily(
                            "InstanceStatus",
                            'Instance Status Check in SID',
                            labels=['SID', 'Instance'])
                        g_instancestatus.add_metric([sid, instance["profile"]],
                                                    {'status': True})
                        yield g_instancestatus
                        pass
                    pass

                if conn:
                    for p in get_instance_servername_list_by_sid(sid):
                        # master identification
                        servername = p['servername']
                        profile = p['profile']
                        kvid_master, kvv_master = c.kv.get(sid + '_master')
                        if kvv_master:
                            kvvDict_master = json.loads(kvv_master['Value'])
                            if servername == kvvDict_master['servername']:
                                # during user count, by user type
                                USRLIST = conn.get_user_list()
                                g_usercount = GaugeMetricFamily(
                                    "UserCount",
                                    'System Overall User Count',
                                    labels=['SID'])
                                g_usercount.add_metric([sid], len(USRLIST))
                                yield g_usercount

                                # during dump count
                                DUMPLIST = conn.get_dump_list()
                                g_dumpcount = GaugeMetricFamily(
                                    "DumpCount",
                                    'System Overall Dump Count',
                                    labels=['SID'])
                                g_dumpcount.add_metric([sid], len(DUMPLIST))
                                yield g_dumpcount

                                # get bk job status
                                job_status = conn.get_bkjob_status_count()
                                g_jobstatus = GaugeMetricFamily(
                                    "BKJobCount",
                                    'Current Background Job Count Status',
                                    labels=['SID', 'BKJobStatus'])
                                g_jobstatus.add_metric([sid, 'Finish'],
                                                       job_status['finish'])
                                g_jobstatus.add_metric([sid, 'Running'],
                                                       job_status['running'])
                                g_jobstatus.add_metric([sid, 'Cancel'],
                                                       job_status['cancel'])
                                yield g_jobstatus
                        else:
                            c.kv.put(sid + '_master',
                                     json.dumps({"servername": servername}))
                            # during user count, by user type
                            USRLIST = conn.get_user_list()
                            g_usercount = GaugeMetricFamily(
                                "UserCount",
                                'System Overall User Count',
                                labels=['SID'])
                            g_usercount.add_metric([sid], len(USRLIST))
                            yield g_usercount

                            # during dump count
                            DUMPLIST = conn.get_dump_list()
                            g_dumpcount = GaugeMetricFamily(
                                "DumpCount",
                                'System Overall Dump Count',
                                labels=['SID'])
                            g_dumpcount.add_metric([sid], len(DUMPLIST))
                            yield g_dumpcount

                            # get bk job status
                            job_status = conn.get_bkjob_status_count()
                            g_jobstatus = GaugeMetricFamily(
                                "BKJobCount",
                                'Current Background Job Count Status',
                                labels=['SID', 'BKJobStatus'])
                            g_jobstatus.add_metric([sid, 'Finish'],
                                                   job_status['finish'])
                            g_jobstatus.add_metric([sid, 'Running'],
                                                   job_status['running'])
                            g_jobstatus.add_metric([sid, 'Cancel'],
                                                   job_status['cancel'])
                            yield g_jobstatus

                        # during workprocess count, by wp type
                        wplist = conn.get_server_wp_list(servername)
                        running_dia_count = 0
                        running_upd_count = 0
                        running_btc_count = 0
                        for wp in wplist:
                            if wp['WP_ISTATUS'] != 2:
                                if wp['WP_TYP'] == 'DIA':
                                    running_dia_count += 1
                                    pass
                                if wp['WP_TYP'] == 'BTC':
                                    running_btc_count += 1
                                    pass
                                if wp['WP_TYP'] == 'UPD':
                                    running_upd_count += 1
                                    pass
                        g_wpcount = GaugeMetricFamily(
                            "WorkprocessCount",
                            'WorkprocessCount of One Instance in SID group by Type',
                            labels=['SID', 'Instance', 'WorkprocessType'])
                        g_wpcount.add_metric([sid, profile, 'DIA'],
                                             running_dia_count)
                        g_wpcount.add_metric([sid, profile, 'BTC'],
                                             running_btc_count)
                        g_wpcount.add_metric([sid, profile, 'UPD'],
                                             running_upd_count)
                        yield g_wpcount

                        # st02 data by instance
                        st02data = conn.get_st02_data()
                        st02data['instance'] = profile
                        g_st02_sapmemory = GaugeMetricFamily(
                            "SAPMemory",
                            'SAP Memory Current Use % in TCode ST02',
                            labels=[
                                'SID', 'Instance', 'SAPMemoryCurrentUsePercent'
                            ])
                        g_st02_sapmemory.add_metric(
                            [sid, profile, 'PageArea'],
                            round(
                                float(st02data['PAGING_AREA']['CURR_USED']) /
                                float(st02data['PAGING_AREA']['AREA_SIZE']), 4)
                            * 100)
                        g_st02_sapmemory.add_metric(
                            [sid, profile, 'ExtendedMemory'],
                            round(
                                float(
                                    st02data['EXTENDED_MEMORY_USAGE']['USED'])
                                / float(st02data['EXTENDED_MEMORY_USAGE']
                                        ['TOTAL']), 4) * 100)
                        g_st02_sapmemory.add_metric(
                            [sid, profile, 'HeapMemory'],
                            round(
                                float(st02data['HEAP_MEMORY_USAGE']['USED']) /
                                float(st02data['HEAP_MEMORY_USAGE']['TOTAL']),
                                4) * 100)
                        yield g_st02_sapmemory

                        g_st02_callstatics = GaugeMetricFamily(
                            "CallStatistics",
                            'SAP Call Statistics HitRadio % in TCode ST02',
                            labels=[
                                'SID', 'Instance',
                                'CallStatisticsHitRadioPercent'
                            ])
                        g_st02_callstatics.add_metric(
                            [sid, profile, 'DIRECT'],
                            st02data['TOTAL_HITRATIO']['DIRECT'])
                        g_st02_callstatics.add_metric(
                            [sid, profile, 'SEQUENTIAL'],
                            st02data['TOTAL_HITRATIO']['SEQUENTIAL'])
                        g_st02_callstatics.add_metric(
                            [sid, profile, 'AVERAGE'],
                            st02data['TOTAL_HITRATIO']['AVERAGE'])
                        yield g_st02_callstatics

                        # es = Elasticsearch(hosts=[{
                        #     "host": "{master_ip}",
                        #     "port": 23392
                        # }])
                        # es.index(
                        #     index="ST02",
                        #     body=st02data,
                        # )

                        # st03 summary data by instance
                        st03detail_summary = conn.get_st03_data_summary()
                        st03detail = {}
                        st03detail['instance'] = profile
                        st03detail['SUMMARY'] = st03detail_summary
                        g_st03detail_steps = GaugeMetricFamily(
                            "DialogSteps",
                            'Dialog Steps in TCode ST03',
                            labels=['SID', 'Instance', 'DialogSteps'])
                        g_st03detail_averageRespTime = GaugeMetricFamily(
                            "AverageRespTime",
                            'Average Resp Time in TCode ST03',
                            labels=['SID', 'Instance', 'AverageRespTime'])
                        g_st03detail_averageDBTime = GaugeMetricFamily(
                            "AverageDBTime",
                            'Average DB Time in TCode ST03',
                            labels=['SID', 'Instance', 'AverageDBTime'])

                        for sumary in st03detail_summary:
                            g_st03detail_steps.add_metric(
                                [sid, profile, sumary['TASKTYPE']],
                                float(sumary['COUNT']))
                            g_st03detail_averageRespTime.add_metric(
                                [sid, profile, sumary['TASKTYPE']],
                                round(
                                    float(sumary['RESPTI']) /
                                    float(sumary['COUNT'])))
                            # g_st03detail_averageDBTime.add_metric(
                            #     [sid, profile, sumary['TASKTYPE']],
                            #     round(sumary['RESPTI'] / sumary['COUNT']))

                        yield g_st03detail_steps
                        yield g_st03detail_averageRespTime

                        # es.index(
                        #     index="ST03",
                        #     body=st03detail,
                        # )

                    conn.close()
        '''
        during job count, by job type
        during rfc resource, total and remain
        during transport list, total
        '''
        # c = CounterMetricFamily("HttpRequests", 'Help text', labels=['app'])
        # c.add_metric(["example"], random.randint(10, 100))
        # yield c

        # bucket1_value = random.randint(0, 10)
        # bucket2_value = random.randint(11, 100)
        # h = HistogramMetricFamily("HistogramMetricFamily",
        #                           'HistogramMetricFamily text',
        #                           labels=['HistogramMetricFamily app'])
        # # h.add_metric(["labels1", "labels2"], [["1", 1], ["2", 1]], 2)
        # h.add_metric(["labels1"], [["1", 1], ["2", 1]], 2)
        # yield h

        # i = InfoMetricFamily("InfoMetricFamily",
        #                      'InfoMetricFamily text',
        #                      labels=['InfoMetricFamily'])
        # i.add_metric(["InfoMetricFamily example"],
        #              {"InfoMetricFamily example": '123'})
        # yield i


while True:
    try:
        c = consul.Consul(host=os.environ.get('CONSUL_HOST')
                          if os.environ.get('CONSUL_HOST') else '127.0.0.1',
                          port=23345,
                          scheme='http')
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        c.agent.service.register(name=hostname + '_agent',
                                 address=ip,
                                 port=23310,
                                 tags=['sapspa_agent', 'sapspa'],
                                 enable_tag_override=True)

        c.agent.service.register(name=hostname + '_host',
                                 address=ip,
                                 port=23311,
                                 tags=['host', 'sapspa'],
                                 enable_tag_override=True)
        break
    except:
        continue

# update filebeat config yaml
if not os.path.exists('/etc/filebeat'):
    os.mkdir('/etc/filebeat')
if not os.path.exists('/etc/filebeat/inputs.d'):
    os.mkdir('/etc/filebeat/inputs.d')

input_path_list = []
sidList = get_sid_list()
for sid in sidList:
    profilepath = '/sapmnt/' + sid + '/profile'
    list1 = os.listdir(profilepath)
    for l in list1:
        m = re.match(sid + '_[A-Z0-9]+_[a-zA-Z0-9]+', l)
        if m and m.group() == l:
            arr = l.split('_')
            instanceid = arr[1]
            input_path_list.append(f'/usr/sap/{sid}/{instanceid}/work/*')

with open('/etc/filebeat/inputs.d/sapspa.yml', 'w') as f:
    filebeat_input_list: List[Dict] = []
    filebeat_input_list.append({
        'type': 'log',
        'paths': input_path_list,
        'scan_frequency': '10s'
    })
    f.write(yaml.dump(filebeat_input_list))
    pass

# post sap instance and host info to master
subapp_list: List[Dict] = []
for sid in sidList:
    subapp: Dict = {}
    subapp['sid'] = sid
    instance_list: List[Dict] = []
    for instance in get_instance_list_by_sid(sid):
        instance_list.append(instance)
    subapp['instance'] = instance_list
    # cat /etc/services | grep sapmsDM0 |awk '{print $2}'
    # get_sapmsserv_cmd = "cat /etc/services | grep sapms%s |awk '{print $2}'" % sid
    get_sapmsserv_cmd = "cat /etc/services"
    get_sapmsserv_cmd_args = shlex.split(get_sapmsserv_cmd)
    sp = subprocess.run(get_sapmsserv_cmd_args, capture_output=True)
    outputlist = sp.stdout.decode('utf-8').split("\n")
    for l in outputlist:
        if "sapms%s" % sid in l:
            msbs = l.split('\t')
            servb = msbs[1]
            serv = servb.split('/')[0]
            subapp['msserv'] = int(serv)
            break
    subapp_list.append(subapp)

hdb_list: List[Dict] = []
for sid in get_hdb_sid_list():
    hdbapp: Dict = {}
    hdbapp['sid'] = sid
    instance_list: List[Dict] = []
    for instance in get_hdb_list_by_sid(sid):
        instance_list.append(instance)
    hdbapp['instance'] = instance_list
    hdbapp['msserv'] = '00'
    hdb_list.append(hdbapp)

post_dict = {"host": get_host_info(), "app": subapp_list, "hdb": hdb_list}
print(post_dict)

r = requests.post(f'http://{master_ip}:23381/api/v1/agents',
                  data=json.dumps(post_dict),
                  headers={'Content-Type': 'application/json'})
print(r.text)

REGISTRY.register(SAPCollector())
# Add prometheus wsgi middleware to route /metrics requests
app_dispatch = DispatcherMiddleware(app, {'/metrics': make_wsgi_app()})

# # Install uwsgi if you do not have it
# pip install uwsgi
# uwsgi --http 0.0.0.0:23310 --wsgi-file sapspa_agent.py --callable app_dispatch
