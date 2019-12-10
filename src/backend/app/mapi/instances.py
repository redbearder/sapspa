from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required
from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import InstanceModel, InstanceSchema

instance_schema = InstanceSchema()
instances_schema = InstanceSchema(many=True)


class Instances(Resource):
    @jwt_required
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("pagesize", 50, type=int), 100)
        data = InstanceModel.query.paginate(page, pagesize)
        # data = App.query.all()
        instances_result = instances_schema.dump(data.items)
        return query_request(instances_result)

    @jwt_required
    def post(self):
        # 新增数据
        data = request.get_json()
        instanceschema = instance_schema.load(data)
        instance = InstanceModel(**instanceschema)
        db.session.add(instance)
        db.session.commit()
        return normal_request("create instance success")


class Instace(Resource):
    @jwt_required
    def get(self, instid):
        # 返回所有数据
        app = InstanceModel.query.get(instid)
        app_result = instance_schema.dump(app)
        return query_request(app_result)

    @jwt_required
    def put(self, instid):
        data = request.get_json()
        app = InstanceModel.query.filter_by(instid=instid).update(data)
        db.session.commit()
        return normal_request("update instance success")


class InstancesInSubApp(Resource):
    @jwt_required
    def get(self, subappid):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("pagesize", 50, type=int), 100)
        instances = InstanceModel.query.filter_by(subappid=subappid).order_by(
            InstanceModel.createdAt.desc()).paginate(page, pagesize)
        instances_result = instances_schema.dump(instances)
        return query_request(instances_result)


class InstancesInHost(Resource):
    @jwt_required
    def get(self, hostid):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("pagesize", 50, type=int), 100)
        instances = InstanceModel.query.filter_by(hostid=hostid).order_by(
            InstanceModel.createdAt.desc()).paginate(page, pagesize)
        instances_result = instances_schema.dump(instances)
        return query_request(instances_result)
