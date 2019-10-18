from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
from app import db
from app.mapi import bp
from app.mapi.auth import basic_auth, token_auth
from app.models import UserModel, UserSchema
from app.utils import bad_request, normal_request, query_request

users_schema = UserSchema(many=True)
user_schema = UserSchema()


class Tokens(Resource):
    def post(self):
        # 新增数据
        data = request.get_json()
        appschema = user_schema.load(data)
        app = UserSchema(**appschema)
        db.session.add(app)
        db.session.commit()
        return normal_request("create app success")


class Token(Resource):
    def delete(self):
        # 新增数据
        data = request.get_json()
        appschema = user_schema.load(data)
        app = UserSchema(**appschema)
        db.session.add(app)
        db.session.commit()
        return normal_request("create app success")


@bp.route('/tokens', methods=['POST'])
@basic_auth.login_required
def get_token():
    token = g.current_user.get_token()
    db.session.commit()
    return jsonify({'token': token})


@bp.route('/tokens', methods=['DELETE'])
@token_auth.login_required
def revoke_token():
    g.current_user.revoke_token()
    db.session.commit()
    return '', 204
