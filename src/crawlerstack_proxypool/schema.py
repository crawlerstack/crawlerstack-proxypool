"""schema"""
import ipaddress

from httpx import URL
from pydantic import AnyUrl, BaseModel, validator

from crawlerstack_proxypool.utils import ALLOW_PROXY_SCHEMA


class SceneIpProxy(BaseModel):
    """scene ip proxy"""
    name: str
    url: URL | str

    @validator('url')
    def check_url(cls, value: URL | str):  # noqa
        if isinstance(value, str):
            value = URL(value)

        if (
                value.is_absolute_url
                and ipaddress.ip_address(value.host)
                and value.scheme in ALLOW_PROXY_SCHEMA
        ):
            return value

    class Config:
        arbitrary_types_allowed = True


class CheckedProxy(BaseModel):
    """Scene update"""
    url: URL
    name: str
    alive: bool

    @validator('url')
    def check_url(cls, value: URL):  # noqa
        if (
                value.is_absolute_url
                and ipaddress.ip_address(value.host)
                and value.scheme in ALLOW_PROXY_SCHEMA
        ):
            return value

    class Config:
        arbitrary_types_allowed = True

    def get_alive_status(self) -> int:
        if self.alive:
            return 1
        return -1


class SceneIpProxyWithRegion(BaseModel):
    name: str
    ip: str
    protocol: str
    port: int
    region: str
