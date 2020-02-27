from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import InstanceModel, InstanceSchema

instance_schema = InstanceSchema()
instances_schema = InstanceSchema(many=True)


class Instances(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = InstanceModel.query.paginate(page, pagesize)
        # data = App.query.all()
        instances_result = instances_schema.dump(data.items)
        return query_request(instances_result)

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
