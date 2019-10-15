# coding:utf-8
from flask_restful import Api, Resource

from app.api import bp
from app.api.apps import App, Apps
from app.api.subapps import SubApp, SubApps
from app.api.hosts import Host, Hosts

api = Api(bp)

api.add_resource(Apps, "/apps")
api.add_resource(App, "/apps/<appid>")

api.add_resource(SubApps, "/subapps")
api.add_resource(SubApp, "/subapps/<subappid>")

api.add_resource(Hosts, "/hosts")
api.add_resource(Host, "/hosts/<hostid>")
