from flask import abort, g, jsonify, request, url_for
from flask_restful import Api, Resource
import json
from app import db
from app.utils import bad_request, normal_request, query_request
from app.models import SubappModel, SubappSchema, InstanceModel, InstanceSchema, HostModel, HostSchema

subapps_schema = SubappSchema(many=True)
subapp_schema = SubappSchema()
host_schema = HostSchema()
instance_schema = InstanceSchema()


class Agents(Resource):
    def get(self):
        # 返回所有数据
        pass

    def post(self):
        data = request.get_json()
        host_info = data['host']
        subapp_list = data['app']
        hdbapp_list = data['hdb'] if "hdb" in data else []
        """
        {
            "host": {
                "cpu": 16,
                "mem": 135204020224,
                "swap": 68728909824,
                "hostname": "s4ides1",
                "ip": [
                    {
                        "device": "eth0",
                        "ip": "172.16.0.190"
                    },
                    {
                        "device": "docker0",
                        "ip": "172.17.0.1"
                    }
                ]
            },
            "app": [
                {
                    "sid": "DM0",
                    "instance": [
                        {
                            "profile": "DM0_D00_s4ides1",
                            "sysnr": "00",
                            "host": "s4ides1",
                            "sid": "DM0",
                            "servername": "s4ides1_DM0_00",
                            "type": "DIALOG"
                        },
                        {
                            "profile": "DM0_ASCS01_s4ides1",
                            "sysnr": "01",
                            "host": "s4ides1",
                            "sid": "DM0",
                            "servername": "s4ides1_DM0_01",
                            "type": "ASCS"
                        }
                    ]
                }
            ]
        }
        """
        oldhost = HostModel.query.filter_by(
            hostname=host_info['hostname']).first()
        if oldhost:
            hostid = oldhost.hostid
        else:
            hostschema = host_schema.load({
                "hostname":
                host_info['hostname'],
                "ipaddress":
                json.dumps(host_info['ip']),
                "cpu":
                host_info['cpu'],
                "memory":
                host_info['mem'],
            })

            host = HostModel(**hostschema)
            db.session.add(host)
            db.session.commit()
            hostid = host.hostid
        for subapp in subapp_list:
            oldsubapp = SubappModel.query.filter_by(
                subappsid=subapp['sid']).first()
            if oldsubapp:
                subappid = oldsubapp.subappid
            else:
                subappschema = subapp_schema.load({
                    "subappsid":
                    subapp['sid'],
                    "subappmsserv":
                    subapp['msserv']
                })
                subapp_model = SubappModel(**subappschema)
                db.session.add(subapp_model)
                db.session.commit()
                subappid = subapp_model.subappid
            for instance in subapp['instance']:
                oldinstance = InstanceModel.query.filter_by(
                    instanceid=instance['profile']).first()
                if oldinstance:
                    pass
                else:
                    instanceschema = instance_schema.load({
                        "instanceid":
                        instance['profile'],
                        "instanceno":
                        instance['sysnr'],
                        "instancetype":
                        instance['type'],
                        "subappid":
                        subappid,
                        "hostid":
                        hostid,
                    })
                    instance_model = InstanceModel(**instanceschema)
                    db.session.add(instance_model)
                    db.session.commit()

            for hdbapp in hdbapp_list:
                oldsubapp = SubappModel.query.filter_by(
                    subappsid=hdbapp['sid']).first()
                if oldsubapp:
                    subappid = oldsubapp.subappid
                else:
                    subappschema = subapp_schema.load({
                        "subappsid":
                        hdbapp['sid'],
                        "subappmsserv":
                        hdbapp['msserv']
                    })
                    subapp_model = SubappModel(**subappschema)
                    db.session.add(subapp_model)
                    db.session.commit()
                    subappid = subapp_model.subappid
                for instance in hdbapp['instance']:
                    oldinstance = InstanceModel.query.filter_by(
                        instanceid=instance['profile']).first()
                    if oldinstance:
                        pass
                    else:
                        instanceschema = instance_schema.load({
                            "instanceid":
                            instance['profile'],
                            "instanceno":
                            instance['sysnr'],
                            "instancetype":
                            instance['type'],
                            "subappid":
                            subappid,
                            "hostid":
                            hostid,
                        })
                        instance_model = InstanceModel(**instanceschema)
                        db.session.add(instance_model)
                        db.session.commit()

        return normal_request("collect agent info success")
