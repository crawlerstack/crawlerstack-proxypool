"""
repository
"""

from crawlerstack_proxypool.repositories.ip import IpRepository
from crawlerstack_proxypool.repositories.proxy import ProxyRepository
from crawlerstack_proxypool.repositories.region import RegionRepository
from crawlerstack_proxypool.repositories.scene import SceneProxyRepository

__all__ = [
    'IpRepository',
    'ProxyRepository',
    'RegionRepository',
    'SceneProxyRepository',
]
