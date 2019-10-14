from flask import jsonify, request, url_for, g, abort
from flask_restful import Resource, Api
from app import db
from app.models import AppModel, AppSchema
from app.api.utils import bad_request, query_request, normal_request

apps_schema = AppSchema(many=True)
app_schema = AppSchema()


class Apps(Resource):
   def get(self):
     #返回所有数据
     page = request.args.get('page', 1, type=int)
     pagesize = min(request.args.get('pagesize', 50, type=int), 100)
     data = AppModel.query.paginate(page, pagesize)
     # data = App.query.all()
     apps_result = apps_schema.dump(data.items)
     return query_request(apps_result)
   def post(self):
     #新增数据
     data = request.get_json()
     return 'add new data: %s'%data


class App(Resource):
   def get(self, appid):
     #返回所有数据
     app = AppModel.query.get(appid)
     app_result = app_schema.dump(app)
     return {"data": app_result}
     return 'this is data list'
   def post(self, appid):
     #新增数据
     data = request.get_json()
     return 'add new data: %s'%data
