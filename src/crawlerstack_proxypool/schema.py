"""schema"""
import ipaddress

from httpx import URL
from pydantic import BaseModel, validator, AnyUrl

from crawlerstack_proxypool.utils import ALLOW_PROXY_SCHEMA


class SceneIpProxy(BaseModel):
    """scene ip proxy"""
    name: str
    ip: str
    protocol: str
    port: int


class SceneProxyUpdate(BaseModel):
    """Scene update"""
    proxy: URL
    name: str

    @validator('proxy')
    def check_proxy(cls, value: URL):   # noqa
        if (value.is_absolute_url
                and ipaddress.ip_address(value.host)
                and value.scheme in ALLOW_PROXY_SCHEMA):
            return value

    class Config:
        arbitrary_types_allowed = True


class SceneIpProxyWithRegion(BaseModel):
    name: str
    ip: str
    protocol: str
    port: int
    region: str
