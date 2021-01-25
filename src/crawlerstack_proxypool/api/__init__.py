import sys
from typing import Optional

from twisted import internet
from twisted.internet import reactor
from twisted.python import log
from twisted.web import resource
from twisted.web.server import Site

from crawlerstack_proxypool.api.services import ProxyIPService
from crawlerstack_proxypool.config import settings


def run(_server, host: Optional[str] = None, port: Optional[int] = None):
    host = host or settings.get('HOST')
    port = port or settings.get('PORT')

    internet.endpoints.TCP4ServerEndpoint(
        reactor, port, interface=host
    ).listen(Site(resource.IResource(ProxyIPService(_server))))

    log.startLogging(sys.stdout)
