from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import SubappModel, SubappSchema, InstanceModel, InstanceSchema, OperationModel, OperationSchema, OperationSubModel, OperationSubSchema
import json
import requests
import threading
import time
from app import create_app

subapps_schema = SubappSchema(many=True)
subapp_schema = SubappSchema()
instance_schema = InstanceSchema()
instances_schema = InstanceSchema(many=True)


def operation_func(**kwargs):
    if "inst" in kwargs:
        pass
    if 'instlist' in kwargs:
        instlist = kwargs['instlist']
        sequence = None
        opid = None
        glist = []
        innerlist = []
        for i in range(len(instlist)):
            if not sequence:
                innerlist.append(instlist[i])
                sequence = instlist[i]['operationsubsequence']
                opid = instlist[i]['operationid']
            elif sequence != instlist[i]['operationsubsequence']:
                glist.append(innerlist)
                innerlist = []
                innerlist.append(instlist[i])
                sequence = instlist[i]['operationsubsequence']
            else:
                innerlist.append(instlist[i])

            if i == len(instlist) - 1:
                glist.append(innerlist)

        for g in glist:
            opsubidlist = []
            for inst in g:
                opsubidlist.append(inst['operationsubid'])
                detail = inst['operationsubdetail']
                if detail['method'] == 'DELETE':
                    # time.sleep(3)
                    r = requests.delete(detail['url'])

                if detail['method'] == 'POST':
                    # time.sleep(3)
                    r = requests.post(detail['url'])

            loop_threshold = 10
            loop_count = 0
            while True:
                assertstatuscount = 0
                for inst in g:
                    detail = inst['operationsubdetail']
                    r = requests.get(detail['url'])
                    if r.text == inst['operationsubstatusassert']:
                        assertstatuscount += 1
                    # time.sleep(3)
                    # assertstatuscount += 1
                if assertstatuscount == len(g):
                    app = create_app()
                    with app.app_context():
                        opsub = OperationSubModel.query.filter(
                            OperationSubModel.operationsubid.in_(
                                opsubidlist)).update({"operationsubstatus": 1},
                                                     synchronize_session=False)
                        db.session.commit()
                    break
                time.sleep(3)
                loop_count += 1
                if loop_count == loop_threshold:
                    return

        app = create_app()
        with app.app_context():
            op = OperationModel.query.get(opid)
            op.operationstatus = 1
            db.session.commit()


class SubApps(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = SubappModel.query.paginate(page, pagesize)
        datacount = SubappModel.query.count()
        subapps_result = subapps_schema.dump(data.items)
        return query_request({'rows': subapps_result, 'count': datacount})

    def post(self):
        data = request.get_json()
        appschema = subapp_schema.load(data)
        app = SubappModel(**appschema)
        db.session.add(app)
        db.session.commit()
        return normal_request("create subapp success")


class SubApp(Resource):
    def get(self, subappid):
        # 返回所有数据
        app = SubappModel.query.get(subappid)
        app_result = subapp_schema.dump(app)
        return query_request(app_result)

    def put(self, subappid):
        data = request.get_json()
        app = SubappModel.query.filter_by(subappid=subappid).update(data)
        db.session.commit()
        return normal_request("update subapp success")


class SubAppsInApp(Resource):
    def get(self, appid):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        subapps = SubappModel.query.filter_by(appid=appid).order_by(
            SubappModel.createdAt.desc()).paginate(page, pagesize)
        datacount = SubappModel.query.filter_by(appid=appid).order_by(
            SubappModel.createdAt.desc()).count()
        subapps_result = subapps_schema.dump(subapps.items)
        return query_request({'rows': subapps_result, 'count': datacount})


class SubAppStatus(Resource):
    def post(self, subappid):
        # start instance
        instList = InstanceModel.query.filter_by(subappid=subappid).all()

        opModel = OperationModel()

        db.session.add(opModel)
        db.session.flush()

        sequenceInstanceType = [
            'WEBDISPATCHER', 'TREX', 'J2EE', 'DIALOG', 'ASCS', 'HDB'
        ]
        sequenceInstanceType = sequenceInstanceType[::-1]

        newInstList = []
        for inst in instList:
            ipaddressarr = json.loads(inst.host.ipaddress)
            opsub = {}
            opsub['operationid'] = opModel.operationid
            opsub['instanceid'] = inst.instid
            opsub['operationsubtype'] = 'START'
            opsub['operationsubdetail'] = {
                "type": "HTTP",
                "method": "POST",
                "url":
                f"http://{ipaddressarr[0]['ip']}:23310/api/apps/{inst.subapp.subappsid}/instances/{inst.instanceno}/status",
                "param": {}
            }
            opsub['operationsubcomment'] = f'Start Instance {inst.instid}'
            opsub['operationsubsequence'] = sequenceInstanceType.index(
                inst.instancetype) + 1
            opsub['operationsubstatus'] = 0
            opsub['operationsubstatusassert'] = '1'

            newopsub = dict(opsub)
            operationSubSchema = OperationSubSchema().load(opsub)
            opSubModel = OperationSubModel(**operationSubSchema)
            db.session.add(opSubModel)
            db.session.flush()
            newopsub['operationsubid'] = opSubModel.operationsubid
            pass

        db.session.commit()

        newInstList.sort(key=lambda i: i['operationsubsequence'], reverse=True)
        threading.Thread(target=operation_func,
                         name="operation_func_thread",
                         kwargs={
                             "instlist": newInstList
                         }).start()

        return normal_request("create start subapp operation success")

    def delete(self, subappid):
        # stop instance
        instList = InstanceModel.query.filter_by(subappid=subappid).all()

        opModel = OperationModel()

        db.session.add(opModel)
        db.session.flush()

        sequenceInstanceType = [
            'WEBDISPATCHER', 'TREX', 'J2EE', 'DIALOG', 'ASCS', 'HDB'
        ]

        newInstList = []
        for inst in instList:
            ipaddressarr = json.loads(inst.host.ipaddress)
            opsub = {}
            opsub['operationid'] = opModel.operationid
            opsub['instanceid'] = inst.instid
            opsub['operationsubtype'] = 'STOP'
            opsub['operationsubdetail'] = {
                "type": "HTTP",
                "method": "DELETE",
                "url":
                f"http://{ipaddressarr[0]['ip']}:23310/api/apps/{inst.subapp.subappsid}/instances/{inst.instanceno}/status",
                "param": {}
            }
            opsub['operationsubcomment'] = f'Stop Instance {inst.instid}'
            opsub['operationsubsequence'] = sequenceInstanceType.index(
                inst.instancetype) + 1
            opsub['operationsubstatus'] = 0
            opsub['operationsubstatusassert'] = '0'

            newopsub = dict(opsub)

            operationSubSchema = OperationSubSchema().load(opsub)
            opSubModel = OperationSubModel(**operationSubSchema)
            db.session.add(opSubModel)
            db.session.flush()

            newopsub['operationsubid'] = opSubModel.operationsubid
            newInstList.append(newopsub)

        db.session.commit()

        newInstList.sort(key=lambda i: i['operationsubsequence'])
        threading.Thread(target=operation_func,
                         name="operation_func_thread",
                         kwargs={
                             "instlist": newInstList
                         }).start()

        return normal_request("create stop subapp operation success")

    def get(self, subappid):
        pass


class SubAppOperation(Resource):
    def get(self, subappid):
        # get operations list
        instList = InstanceModel.query.filter_by(subappid=subappid).all()
        instidlist = [inst.instid for inst in instList]
        oplist = OperationSubModel.query.filter(
            InstanceModel.instid.in_(instidlist)).all()

        return query_request({
            'rows': OperationSubSchema(many=True).dump(oplist),
            'count': len(oplist)
        })
