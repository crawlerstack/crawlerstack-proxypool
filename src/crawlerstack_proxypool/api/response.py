import json
from typing import Callable

from twisted.web.http import Request


def json_response(func: Callable):
    def _wrapper(request: Request, **kwargs):
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Access-Control-Allow-Origin', '*')
        resp = func(request, **kwargs)
        return json.dumps(resp)

    return _wrapper
