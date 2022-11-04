"""schema"""
import ipaddress

from httpx import URL
from pydantic import BaseModel, validator

from crawlerstack_proxypool.utils import ALLOW_PROXY_SCHEMA


class SceneIpProxy(BaseModel):
    """scene ip proxy"""
    name: str
    url: URL | str

    class Config:
        arbitrary_types_allowed = True

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


class SceneIpProxyStatus(SceneIpProxy):
    """scene ip proxy status"""
    name: str
    url: URL | str
    alive: bool

    def get_alive_status(self) -> int:
        if self.alive:
            return 1
        return -1


class ValidatedProxy(SceneIpProxy):
    """Scene update"""
    url: URL
    name: str
    source: str
    alive: bool
    dest: list[str]

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
