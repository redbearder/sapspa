from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import SubappModel, SubappSchema

subapps_schema = SubappSchema(many=True)
subapp_schema = SubappSchema()


class SubApps(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = SubappModel.query.paginate(page, pagesize)
        subapps_result = subapps_schema.dump(data.items)
        return query_request(subapps_result)

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
