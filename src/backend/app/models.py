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
from marshmallow import (Schema, ValidationError, fields, post_load, pprint,
                         pre_load, validate)
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
    subappurl = db.Column(db.String(100), nullable=False, comment='subapp url')
    subappdesc = db.Column(db.String(100),
                           nullable=True,
                           comment='subapp description')
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
                           nullable=False,
                           comment='host domain name')
    ipaddress = db.Column(db.String(255), nullable=False, comment='ip address')
    cpu = db.Column(db.Integer, nullable=False, comment='cpu')
    memory = db.Column(db.Integer, nullable=False, comment='memory')
    fsmount = db.Column(db.TEXT, nullable=False, comment='file system mount')
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
    subappurl = fields.URL(required=False)
    subappdesc = fields.Str(required=False,
                            validate=validate.Length(min=3, max=255))
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
