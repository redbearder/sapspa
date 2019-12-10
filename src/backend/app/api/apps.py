from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource

from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import AppModel, AppSchema

apps_schema = AppSchema(many=True)
app_schema = AppSchema()


class Apps(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = AppModel.query.paginate(page, pagesize)
        # data = App.query.all()
        apps_result = apps_schema.dump(data.items)
        return query_request(apps_result)

    def post(self):
        # 新增数据
        data = request.get_json()
        appschema = app_schema.load(data)
        app = AppModel(**appschema)
        db.session.add(app)
        db.session.commit()
        return normal_request("create app success")


class App(Resource):
    def get(self, appid):
        # 返回所有数据
        app = AppModel.query.get(appid)
        app_result = app_schema.dump(app)
        return query_request(app_result)

    def put(self, appid):
        # 新增数据
        data = request.get_json()
        app = AppModel.query.filter_by(appid=appid).update(data)
        db.session.commit()
        return normal_request("update app success")
