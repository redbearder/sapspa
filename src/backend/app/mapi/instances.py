from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required
from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import InstanceModel, InstanceSchema, OperationModel, OperationSchema, OperationSubModel, OperationSubSchema
import json
import threading
import requests
import time

instance_schema = InstanceSchema()
instances_schema = InstanceSchema(many=True)


def operation_func(**kwargs):
    if "instlist" in kwargs:
        pass
    if 'inst' in kwargs:
        detail = kwargs['inst']['operationsubdetail']
        if detail['method'] == 'DELETE':
            r = requests.delete(detail['url'])
            if r.status_code == 200:
                opsub = OperationSubModel.query.get(
                    kwargs['inst']['operationsubid'])
                opsub.operationsubstatus = 1
                op = OperationModel.query.get(kwargs['inst']['operationsid'])
                op.operationstatus = 1
                db.session.commit()

        if detail['method'] == 'POST':
            r = requests.post(detail['url'])
            if r.status_code == 200:
                opsub = OperationSubModel.query.get(
                    kwargs['inst']['operationsubid'])
                opsub.operationsubstatus = 1
                op = OperationModel.query.get(kwargs['inst']['operationsid'])
                op.operationstatus = 1
                db.session.commit()
    pass


class Instances(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = InstanceModel.query.paginate(page, pagesize)
        datacount = InstanceModel.query.count()
        instances_result = instances_schema.dump(data.items)
        return query_request({'rows': instances_result, 'count': datacount})

    def post(self):
        # 新增数据
        data = request.get_json()
        instanceschema = instance_schema.load(data)
        instance = InstanceModel(**instanceschema)
        db.session.add(instance)
        db.session.commit()
        return normal_request("create instance success")


class Instace(Resource):
    def get(self, instid):
        # 返回所有数据
        app = InstanceModel.query.get(instid)
        app_result = instance_schema.dump(app)
        return query_request(app_result)

    def put(self, instid):
        data = request.get_json()
        app = InstanceModel.query.filter_by(instid=instid).update(data)
        db.session.commit()
        return normal_request("update instance success")


class InstancesInSubApp(Resource):
    def get(self, subappid):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        instances = InstanceModel.query.filter_by(subappid=subappid).order_by(
            InstanceModel.createdAt.desc()).paginate(page, pagesize)
        instancescount = InstanceModel.query.filter_by(
            subappid=subappid).order_by(
                InstanceModel.createdAt.desc()).count()
        instances_result = instances_schema.dump(instances.items)
        return query_request({
            'rows': instances_result,
            'count': instancescount
        })


class InstancesInHost(Resource):
    def get(self, hostid):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        instances = InstanceModel.query.filter_by(hostid=hostid).order_by(
            InstanceModel.createdAt.desc()).paginate(page, pagesize)
        instancescount = InstanceModel.query.filter_by(hostid=hostid).order_by(
            InstanceModel.createdAt.desc()).count()
        instances_result = instances_schema.dump(instances.items)
        return query_request({
            'rows': instances_result,
            'count': instancescount
        })


class InstaceStatus(Resource):
    def post(self, instid):
        # start instance
        inst = InstanceModel.query.get(instid)

        opModel = OperationModel()

        db.session.add(opModel)
        db.session.flush()

        ipaddressarr = json.loads(inst.host.ipaddress)
        opsub = {}
        opsub['operationid'] = opModel.operationid
        opsub['instanceid'] = instid
        opsub['operationsubtype'] = 'START'
        opsub['operationsubdetail'] = {
            "type": "HTTP",
            "method": "POST",
            "url":
            f"http://{ipaddressarr[0]['ip']}:23310/api/apps/{inst.subapp.subappsid}/instances/{inst.instanceno}/status",
            "param": {}
        }
        opsub['operationsubcomment'] = f'Start Instance {instid}'
        opsub['operationsubsequence'] = 1
        opsub['operationsubstatus'] = 0
        opsub['operationsubstatusassert'] = '1'

        newopsub = dict(opsub)

        operationSubSchema = OperationSubSchema(many=False).load(opsub)
        opSubModel = OperationSubModel(**operationSubSchema)
        db.session.add(opSubModel)

        db.session.commit()

        threading.Thread(target=operation_func,
                         name="operation_func_thread",
                         kwargs={
                             "inst": newopsub
                         }).start()

        return normal_request("create start instance operation success")

    def delete(self, instid):
        # stop instance
        inst = InstanceModel.query.get(instid)

        opModel = OperationModel()

        db.session.add(opModel)
        db.session.flush()

        ipaddressarr = json.loads(inst.host.ipaddress)
        opsub = {}
        opsub['operationid'] = opModel.operationid
        opsub['instanceid'] = instid
        opsub['operationsubtype'] = 'STOP'
        opsub['operationsubdetail'] = {
            "type": "HTTP",
            "method": "DELETE",
            "url":
            f"http://{ipaddressarr[0]['ip']}:23310/api/apps/{inst.subapp.subappsid}/instances/{inst.instanceno}/status",
            "param": {}
        }
        opsub['operationsubcomment'] = f'Stop Instance {instid}'
        opsub['operationsubsequence'] = 1
        opsub['operationsubstatus'] = 0
        opsub['operationsubstatusassert'] = '0'

        newopsub = dict(opsub)

        operationSubSchema = OperationSubSchema().load(opsub)
        opSubModel = OperationSubModel(**operationSubSchema)
        db.session.add(opSubModel)
        db.session.flush()
        newopsub['operationsubid'] = opSubModel.operationsubid
        db.session.commit()

        threading.Thread(target=operation_func,
                         name="operation_func_thread",
                         kwargs={
                             "inst": newopsub
                         }).start()

        return normal_request("create stop instance operation success")

    def get(self, subappid):
        pass


class InstaceOperation(Resource):
    def get(self, instid):
        opList = OperationSubModel.query.filter_by(instanceid=instid).all()

        return query_request({
            'rows': OperationSubSchema(many=True).dump(opList),
            'count': len(opList)
        })
