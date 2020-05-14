import base64
import json
import os
from datetime import datetime, timedelta
from hashlib import md5
from time import time

import jwt
import redis
import rq
from flask import current_app, url_for
from flask_login import UserMixin
from marshmallow import (Schema, ValidationError, fields, pre_dump, pprint,
                         post_load, post_dump, pre_load, validate)
from werkzeug.security import check_password_hash, generate_password_hash

from app import db, login

##### MODELS #####


class UserModel(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.Integer,
                    primary_key=True,
                    autoincrement=True,
                    comment='user unique id')
    username = db.Column(db.String(50),
                         nullable=False,
                         index=True,
                         comment='user name')
    password = db.Column(db.String(100),
                         nullable=False,
                         comment='user password')
    userdomain = db.Column(db.String(100),
                           nullable=False,
                           comment='user domain name')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='user create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='user update datetime')

    def __repr__(self):
        return '<UserModel {}>'.format(self.username)


class AppModel(db.Model):
    __tablename__ = 'app'
    appid = db.Column(db.Integer,
                      primary_key=True,
                      autoincrement=True,
                      comment='app id')
    appname = db.Column(db.String(50),
                        nullable=False,
                        index=True,
                        comment='app name')
    appdesc = db.Column(db.String(100),
                        nullable=False,
                        comment='app description')
    appdomain = db.Column(db.String(100),
                          nullable=False,
                          comment='app domain name')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='app create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='app update datetime')

    def __repr__(self):
        return '<AppModel {}>'.format(self.appname)


class SubappModel(db.Model):
    __tablename__ = 'subapp'
    subappid = db.Column(db.Integer,
                         primary_key=True,
                         autoincrement=True,
                         comment='subapp id')
    subappsid = db.Column(db.String(5),
                          nullable=False,
                          index=True,
                          comment='subapp SID')
    subappmsserv = db.Column(db.String(10),
                             nullable=True,
                             comment='subapp msserv')
    subappurl = db.Column(db.String(100), nullable=True, comment='subapp url')
    subappdesc = db.Column(db.String(100),
                           nullable=True,
                           comment='subapp description')
    subappguiconn = db.Column(
        db.TEXT,
        nullable=True,
        comment='subapp sapgui connection info for login')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='subapp create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='subapp update datetime')


class HostModel(db.Model):
    __tablename__ = 'host'
    hostid = db.Column(db.Integer,
                       primary_key=True,
                       autoincrement=True,
                       comment='host unique id')
    hostname = db.Column(db.String(10),
                         nullable=False,
                         index=True,
                         comment='hostname')
    hostdomain = db.Column(db.String(100),
                           nullable=True,
                           comment='host domain name')
    ipaddress = db.Column(db.String(255), nullable=False, comment='ip address')
    cpu = db.Column(db.Integer, nullable=False, comment='cpu')
    memory = db.Column(db.BigInteger, nullable=False, comment='memory')
    fsmount = db.Column(db.TEXT, nullable=True, comment='file system mount')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='host create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='host update datetime')

    def get_ipaddress_list(self):
        return json.loads(str(self.ipaddress))


class InstanceModel(db.Model):
    __tablename__ = 'instance'
    instid = db.Column(db.Integer,
                       primary_key=True,
                       autoincrement=True,
                       comment='instance unique id')
    instanceid = db.Column(db.String(20),
                           nullable=False,
                           index=True,
                           comment='instance id')
    subappid = db.Column(db.Integer, db.ForeignKey('subapp.subappid'))
    hostid = db.Column(db.Integer, db.ForeignKey('host.hostid'))
    instanceno = db.Column(db.String(5),
                           nullable=False,
                           comment='instance number')
    instancetype = db.Column(db.String(10),
                             nullable=False,
                             comment='instance type')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='instance create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='instance update datetime')
    subapp = db.relationship('SubappModel', foreign_keys=[subappid])
    host = db.relationship('HostModel', foreign_keys=[hostid])


class LoginModel(db.Model):
    __tablename__ = 'saplogin'
    loginid = db.Column(db.Integer,
                        primary_key=True,
                        autoincrement=True,
                        comment='login unique id')
    subappid = db.Column(db.Integer, db.ForeignKey('subapp.subappid'))
    username = db.Column(db.String(50), nullable=False, comment='username')
    password = db.Column(db.String(50), nullable=False, comment='password')
    client = db.Column(db.String(5), nullable=False, comment='client number')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='instance create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='instance update datetime')
    subapp = db.relationship('SubappModel', foreign_keys=[subappid])


class OperationModel(db.Model):
    __tablename__ = 'operation'
    operationid = db.Column(db.Integer,
                            primary_key=True,
                            autoincrement=True,
                            comment='operation unique id')
    operationstatus = db.Column(db.Integer,
                                nullable=False,
                                default=0,
                                comment='operation status')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='operation create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='operation update datetime')


class OperationSubModel(db.Model):
    __tablename__ = 'operationsub'
    operationsubid = db.Column(db.Integer,
                               primary_key=True,
                               autoincrement=True,
                               comment='operationsubid unique id')
    operationid = db.Column(db.Integer, db.ForeignKey('operation.operationid'))
    instanceid = db.Column(db.Integer, db.ForeignKey('instance.instanceid'))
    operationsubtype = db.Column(db.String(50),
                                 nullable=False,
                                 comment='operationsub type')
    operationsubdetail = db.Column(db.TEXT,
                                   nullable=False,
                                   comment='operationsub detail')
    operationsubcomment = db.Column(db.String(250),
                                    nullable=False,
                                    comment='operationsub comment')
    operationsubsequence = db.Column(db.Integer,
                                     nullable=False,
                                     comment='operationsub sequence')
    operationsubstatus = db.Column(db.Integer,
                                   nullable=False,
                                   default=0,
                                   comment='operationsub status')
    createdAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          comment='operationsub create datetime')
    updatedAt = db.Column(db.DateTime,
                          default=db.func.now(),
                          onupdate=db.func.now(),
                          comment='operationsub update datetime')
    instance = db.relationship('InstanceModel', foreign_keys=[instanceid])
    operation = db.relationship('OperationModel', foreign_keys=[operationid])


# Custom validator
def must_not_be_blank(data):
    if not data:
        raise ValidationError("Data not provided.")


##### SCHEMAS #####


class UserSchema(Schema):
    uid = fields.Int(dump_only=True)
    username = fields.Str(required=True,
                          validate=validate.Length(min=5, max=20))
    password = fields.Str(required=True,
                          validate=validate.Length(min=8, max=20))
    userdomain = fields.Str(validate=validate.Length(min=3, max=255))
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class AppSchema(Schema):
    appid = fields.Int(dump_only=True)
    appname = fields.Str(required=True,
                         validate=validate.Length(min=3, max=20))
    appdesc = fields.Str(required=True,
                         validate=validate.Length(min=4, max=100))
    appdomain = fields.Str(validate=validate.Length(min=3, max=255))
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class SubappSchema(Schema):
    subappid = fields.Int(dump_only=True)
    subappsid = fields.Str(required=True, validate=validate.Length(equal=3))
    subappmsserv = fields.Str(required=True)
    subappurl = fields.URL(required=False)
    subappdesc = fields.Str(required=False,
                            validate=validate.Length(min=3, max=255))
    subappguiconn = fields.Str(required=False)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class HostSchema(Schema):
    hostid = fields.Int(dump_only=True)
    hostname = fields.Str(required=True,
                          validate=validate.Length(min=6, max=20))
    hostdomain = fields.Str(required=False,
                            validate=validate.Length(min=4, max=50))
    ipaddress = fields.Str()
    cpu = fields.Int()
    memory = fields.Int()
    fsmount = fields.Str(required=False)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class InstanceSchema(Schema):
    instid = fields.Int(dump_only=True)
    instanceid = fields.Str(required=True,
                            validate=validate.Length(min=10, max=20))
    instanceno = fields.Str(required=True, validate=validate.Length(equal=2))
    subappid = fields.Int(required=True)
    hostid = fields.Int(required=True)
    instancetype = fields.Str(required=True)
    subapp = fields.Nested(SubappSchema)
    host = fields.Nested(HostSchema)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class LoginSchema(Schema):
    loginid = fields.Int(dump_only=True)
    username = fields.Str(required=True,
                          validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True,
                          validate=validate.Length(min=3, max=50))
    client = fields.Str(required=True, validate=validate.Length(equal=3))
    subappid = fields.Int(required=True)
    subapp = fields.Nested(SubappSchema)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class OperationSchema(Schema):
    operationid = fields.Int(dump_only=True)
    operationstatus = fields.Int(required=True)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)


class OperationSubSchema(Schema):
    operationsubid = fields.Int(dump_only=True)
    operationid = fields.Int(required=True)
    instanceid = fields.Int(required=True)
    operation = fields.Nested(OperationSchema)
    instance = fields.Nested(InstanceSchema)
    operationsubtype = fields.Str(required=True,
                                  validate=validate.Length(min=3, max=50))
    operationsubdetail = fields.Str(required=True)
    operationsubcomment = fields.Str(required=True,
                                     validate=validate.Length(min=3, max=250))
    operationsubsequence = fields.Int(required=True)
    operationsubstatus = fields.Int(required=True)
    createdAt = fields.DateTime(dump_only=True)
    updatedAt = fields.DateTime(dump_only=True)

    @pre_load
    def operationsubdetail_obj_to_jsonstr(self, load_data, **kwargs):
        load_data["operationsubdetail"] = json.dumps(
            load_data["operationsubdetail"])
        return load_data

    @pre_load(pass_many=True)
    def operationsubdetail_objs_to_jsonstrs(self, load_datas, many, **kwargs):
        if many:
            for i in range(len(load_datas)):
                load_datas[i]["operationsubdetail"] = json.dumps(
                    load_datas[i]["operationsubdetail"])
            return load_datas
        else:
            load_datas["operationsubdetail"] = json.dumps(
                load_datas["operationsubdetail"])
            return load_datas

    @post_dump
    def operationsubdetail_jsonstr_to_obj(self, dump_data, **kwargs):
        dump_data["operationsubdetail"] = json.loads(
            dump_data["operationsubdetail"])
        return dump_data

    @post_dump(pass_many=True)
    def operationsubdetail_jsonstrs_to_objs(self, dump_datas, many, **kwargs):
        if many:
            for i in range(len(dump_datas)):
                dump_datas[i]["operationsubdetail"] = json.loads(
                    dump_datas[i]["operationsubdetail"])
            return dump_datas
        else:
            dump_datas["operationsubdetail"] = json.loads(
                dump_datas["operationsubdetail"])
            return dump_datas
