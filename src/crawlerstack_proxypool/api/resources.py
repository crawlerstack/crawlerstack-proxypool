import json
from typing import Dict, List, Optional, Set, Tuple, Union

from twisted.python.reflect import prefixedMethodNames
from twisted.web import resource
from twisted.web.http import Request
from twisted.web.resource import Resource
from zope.interface import implementer

from crawlerstack_proxypool.api.exceptions import ObjectNotFound
from crawlerstack_proxypool.config import settings


@implementer(resource.IResource)
class JsonResource(Resource):
    # isLeaf = True

    def __init__(self, root, service):
        super().__init__()
        self.root = root
        self.service = service

        self.load_child()

    def load_child(self):
        pass

    def getChild(self, path, request):
        if path == b'':
            return self
        return Resource.getChild(self, path, request)

    def render(self, request: Request):
        try:
            response = super().render(request)
            status_code = 200
        except Exception as e:
            status_code, response = self.handle_exception(e)
        return self.render_object(response, request, status_code)

    def handle_exception(self, exception):
        data = {
            'detail': str(exception)
        }
        status_code = 500
        if isinstance(exception, ObjectNotFound):
            status_code = 404
        return status_code, data

    def render_object(
            self,
            response: Union[Dict, List, Set, Tuple, int, str, bool],
            request: Request,
            status_code: Optional[int] = 200,
    ):
        response = json.dumps(response)
        request.setResponseCode(status_code)
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.setHeader('Access-Control-Allow-Methods', ' '.join(self.allow_methods()))
        request.setHeader('Access-Control-Allow-Headers', ' X-Requested-With')
        request.setHeader('Content-Length', str(len(response)))
        return response.encode('utf-8')

    def allow_methods(self):
        try:
            methods = self.allowedMethods
        except AttributeError:
            methods = self.extract_allow_methods()
        return methods

    def extract_allow_methods(self):
        methods = []
        for name in prefixedMethodNames(self.__class__, "render_"):
            if name.isupper():
                methods.append(name)
        return methods


doc = """
Usage:

+--------+----------------------------------------+--------------------------------+
| method |                   url                  |             response           |
+--------+----------------------------------------+--------------------------------+
|   GET  |  /proxy_ip/<string:scene>              | {"ip": <ip>}                   |
|   GET  |  /proxy_ip/<string:scene>?ip=<ip>      |                {}              |
+--------+----------------------------------------+--------------------------------+
"""


class RootResource(JsonResource):
    def __init__(self, service):
        self.scene_names = self.load_scene_names()
        self.base_url = f'http://{settings.get("HOST")}:{settings.get("PORT")}'
        super().__init__(self, service)

    def load_child(self):
        self.putChild('proxy_ip'.encode(), ProxyIpResource(self, self.service))

    @staticmethod
    def load_scene_names():
        names = []
        scene_tasks = settings.get('SCENE_TASKS')
        for task in scene_tasks:
            names.append(task.get('name'))
        return names

    def render_GET(self, request):
        return {
            'links': {
                'href': f'http://{settings.get("HOST")}:{settings.get("PORT")}/proxy_ip',
                'method': 'GET'
            }
        }


class ProxyIpResource(JsonResource):

    def load_child(self):
        for scene in self.root.scene_names:  # type: str
            self.putChild(scene.encode(), SceneProxyIPResource(self.root, scene, self.service))

    def render_GET(self, request: Request):
        scenes = []
        for scene in self.root.scene_names:
            scenes.append(
                {
                    'scene': scene,
                    'links': [
                        {
                            'href': f'{self.root.base_url}/proxy_ip/{scene}',
                            'method': 'GET'
                        },
                        {
                            'href': f'{self.root.base_url}/proxy_ip/{scene}/<ip>',
                            'method': 'GET',
                            'desc': 'You should replace `<ip>` to you selected ip, to decrease the ip score. '
                        }
                    ]
                }
            )
        return {'scenes': scenes}


class SceneProxyIPResource(JsonResource):
    def __init__(self, root, scene, service):
        super().__init__(root=root, service=service)
        self.scene = scene

    def render_GET(self, request: Request):
        if request.args:
            ips = request.args.get(b'ip', None)
            if ips:
                ip = ips[0].decode()
                self.service.update(self.scene, ip)
                return {}
            msg = f'parameters <ip> not found'
        else:
            ip = self.service.select(self.scene)
            if ip:
                return {
                    'ip': ip
                }
            msg = f'scene <{self.scene}> has no proxy ip to use.'
        raise ObjectNotFound(msg)


@implementer(resource.IResource)
class DemoResource(resource.Resource):

    def __init__(self, service):
        resource.Resource.__init__(self)
        self.service = service

    def render_GET(self, request):
        print(self.service.select())
        return b'Hello world'

    def getChild(self, path, request):
        if path == b'':
            return self
