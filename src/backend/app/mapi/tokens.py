from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from flask_jwt_extended import (JWTManager, jwt_required, create_access_token,
                                get_jwt_identity, current_user)

from app import db, jwt
from app.mapi import bp
from app.mapi.auth import basic_auth, token_auth
from app.models import UserModel, UserSchema
from app.utils import bad_request, normal_request, query_request, error_response

users_schema = UserSchema(many=True)
user_schema = UserSchema()


@jwt.unauthorized_loader
def my_expired_token_callback(expired_token):
    return jsonify({
        'success': False,
        'code': 0,
        'msg': 'token auth fail'
    }), 401


@jwt.expired_token_loader
def my_expired_token_callback(expired_token):
    return jsonify({
        'success': False,
        'code': 0,
        'msg': 'Token has expired'
    }), 401


class Tokens(Resource):
    def post(self):
        # 新增数据
        if not request.is_json:
            return bad_request('post json data fail')

        username = request.json.get('username', None)
        password = request.json.get('password', None)
        if not username:
            return bad_request('Missing username parameter')
        if not password:
            return bad_request('Missing password parameter')

        user = UserModel.query.filter_by(username=username,
                                         password=password).first()
        if not user:
            return bad_request('username or password is incorrect')

        # Identity can be any data that is json serializable
        access_token = create_access_token(identity=username)
        return query_request(access_token, "create app success")


class Token(Resource):
    def delete(self):
        # 新增数据
        data = request.get_json()
        appschema = user_schema.load(data)
        app = UserSchema(**appschema)
        db.session.add(app)
        db.session.commit()
        return normal_request("create app success")
