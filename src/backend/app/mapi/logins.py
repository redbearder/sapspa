from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required
from app import db, Config
from app.utils import bad_request, normal_request, query_request
from app.models import LoginModel, LoginSchema
from app.models import SubappModel, SubappSchema
import consul
import json

login_schema = LoginSchema()
logins_schema = LoginSchema(many=True)
subapp_schema = SubappSchema()


class Logins(Resource):
    def get(self):
        # 返回所有数据
        page = request.args.get("page", 1, type=int)
        pagesize = min(request.args.get("limit", 50, type=int), 100)
        data = LoginModel.query.paginate(page, pagesize)
        datacount = LoginModel.query.count()
        logins_result = logins_schema.dump(data.items)
        return query_request({'rows': logins_result, 'count': datacount})

    def post(self):
        # 新增数据
        data = request.get_json()
        subappid = data['subappid']
        loginschema = login_schema.load(data)
        login = LoginModel(**loginschema)
        db.session.add(login)
        db.session.commit()

        subapp_m = SubappModel.query.get(subappid)
        subapp = subapp_schema.dump(subapp_m)
        c = consul.Consul(host='127.0.0.1',
                          port=Config.CONSUL_CLIENT_PORT,
                          scheme='http')
        c.kv.put(
            subapp['subappsid'] + '_login',
            json.dumps({
                "r3client": data['client'],
                "r3user": data['username'],
                "r3pwd": data['password']
            }))
        return normal_request("create instance success")


class Login(Resource):
    def get(self, loginid):
        # 返回所有数据
        app = LoginModel.query.get(loginid)
        app_result = login_schema.dump(app)
        return query_request(app_result)

    def put(self, loginid):
        data = request.get_json()
        subappid = data['subappid']
        app = LoginModel.query.filter_by(loginid=loginid).update(data)
        db.session.commit()

        subapp_m = SubappModel.query.get(subappid)
        subapp = subapp_schema.dump(subapp_m)
        c = consul.Consul(host='127.0.0.1',
                          port=Config.CONSUL_CLIENT_PORT,
                          scheme='http')
        c.kv.put(
            subapp['subappsid'] + '_login',
            json.dumps({
                "r3client": data['client'],
                "r3user": data['username'],
                "r3pwd": data['password']
            }))
        return normal_request("update sap login info success")
