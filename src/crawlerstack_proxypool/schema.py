"""schema"""
import ipaddress
from datetime import datetime
from typing import Any

from httpx import URL
from pydantic import BaseModel, validator

from crawlerstack_proxypool.utils import ALLOW_PROXY_SCHEMA


class SceneIpProxy(BaseModel):
    """scene ip proxy"""
    name: str
    url: URL | str

    class Config:
        """config"""
        arbitrary_types_allowed = True

    @validator('url')
    def check_url(cls, value: URL | str):  # pylint: disable=no-self-argument
        """check url"""
        if isinstance(value, str):
            value = URL(value)

        if (
                value.is_absolute_url
                and ipaddress.ip_address(value.host)
                and value.scheme in ALLOW_PROXY_SCHEMA
        ):
            return value
        raise ValueError('url must be URL object or URL string')


class SceneIpProxyStatus(SceneIpProxy):
    """scene ip proxy status"""
    name: str
    url: URL | str
    alive: bool

    def get_alive_status(self) -> int:
        """get alive status"""
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
        """get alive status"""
        if self.alive:
            return 1
        return -1


class SceneIpProxyWithRegion(BaseModel):
    """scene ip proxy with region"""
    name: str
    ip: str
    protocol: str
    port: int
    region: str


class SceneProxy(BaseModel):
    """scene proxy message"""
    id: int
    name: str
    alive_count: int
    proxy_id: int
    update_time: datetime

    class Config:
        """config"""
        orm_mode = True


class SceneIpProxyCreate(BaseModel):
    """scene ip proxy create"""
    name: str
    url: str

    class Config:
        """config"""
        arbitrary_types_allowed = True

    @validator('url')
    def check_url(cls, value: str):  # pylint: disable=no-self-argument
        """check url"""
        if isinstance(value, str):
            value = URL(value)

        if (
                value.is_absolute_url
                and ipaddress.ip_address(value.host)
                and value.scheme in ALLOW_PROXY_SCHEMA
        ):
            return value
        raise ValueError('url must be URL object or URL string')


class SceneIpProxyMessage(BaseModel):
    """scene ip proxy message"""
    name: str
    url: str | Any

    @validator('url')
    def check_url(cls, value: str | Any):  # pylint: disable=no-self-argument
        """check url"""
        if isinstance(value, URL):
            return f'{value.scheme}://{value.host}:{value.port}'
        return value
