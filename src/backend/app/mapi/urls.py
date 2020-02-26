# coding:utf-8
from flask_restful import Api, Resource

from app.mapi import bp
from app.mapi.apps import App, Apps
from app.mapi.subapps import SubApp, SubApps, SubAppsInApp
from app.mapi.hosts import Host, Hosts
from app.mapi.instances import Instace, Instances, InstancesInSubApp, InstancesInHost
from app.mapi.tokens import Token, Tokens
from app.mapi.logins import Login, Logins

api = Api(bp)

api.add_resource(Apps, "/apps")
api.add_resource(App, "/apps/<appid>")

api.add_resource(SubApps, "/subapps")
api.add_resource(SubApp, "/subapps/<subappid>")
api.add_resource(SubAppsInApp, "/apps/<appid>/subapps")

api.add_resource(Hosts, "/hosts")
api.add_resource(Host, "/hosts/<hostid>")

api.add_resource(Instances, "/instances")
api.add_resource(Instace, "/instances/<instid>")
api.add_resource(InstancesInSubApp, "/subapps/<subappid>/instances")
api.add_resource(InstancesInHost, "/hosts/<hostid>/instances")

api.add_resource(Tokens, "/tokens")
api.add_resource(Token, "/tokens/<token>")

api.add_resource(Logins, "/logins")
api.add_resource(Login, "/logins/<loginid>")
