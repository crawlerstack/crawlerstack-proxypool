from datetime import datetime
from typing import Literal

from pydantic import BaseModel, constr


class BaseEntity(BaseModel):
    id: int

    class Config:
        db_mode = True


class ProxyStatusEntity(BaseEntity):
    proxy_id: int
    name: constr(max_length=255)
    alive_count: int
    elapse_time: int
    update_time: datetime


class IpProxyEntity(BaseEntity):
    ip_id: int
    schema_: constr(max_length=6)
    port: int
    anonymous: Literal[0, 1, 2]

    proxy_status: list[ProxyStatusEntity] = []


class IpAddressEntity(BaseEntity):
    ip: constr(max_length=255)
    ip_proxies: list[IpProxyEntity] = []
