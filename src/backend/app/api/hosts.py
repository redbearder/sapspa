from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import HostModel, HostSchema

host_schema = HostSchema()
hosts_schema = HostSchema(many=True)


class Hosts(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = HostModel.query.paginate(page, pagesize)
        # data = App.query.all()
        hosts_result = hosts_schema.dump(data.items)
        return query_request(hosts_result)

    def post(self):
        # 新增数据
        data = request.get_json()
        hostschema = host_schema.load(data)
        host = HostModel(**hostschema)
        db.session.add(host)
        db.session.commit()
        return normal_request("create host success")


class Host(Resource):
    def get(self, hostid):
        # 返回所有数据
        app = HostModel.query.get(hostid)
        app_result = host_schema.dump(app)
        return query_request(app_result)

    def put(self, hostid):
        # 新增数据
        data = request.get_json()
        app = HostModel.query.filter_by(hostid=hostid).update(data)
        db.session.commit()
        return normal_request("update host success")
