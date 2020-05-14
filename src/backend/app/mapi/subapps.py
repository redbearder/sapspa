from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import SubappModel, SubappSchema, InstanceModel, InstanceSchema, OperationModel, OperationSchema, OperationSubModel, OperationSubSchema
import json

subapps_schema = SubappSchema(many=True)
subapp_schema = SubappSchema()
instance_schema = InstanceSchema()
instances_schema = InstanceSchema(many=True)


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

            operationSubSchema = OperationSubSchema().load(opsub)
            opSubModel = OperationSubModel(**operationSubSchema)
            db.session.add(opSubModel)
            pass

        db.session.commit()
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

            operationSubSchema = OperationSubSchema().load(opsub)
            opSubModel = OperationSubModel(**operationSubSchema)
            db.session.add(opSubModel)

        db.session.commit()
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
