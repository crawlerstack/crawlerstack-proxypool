from datetime import datetime
from typing import TypeVar

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship


class CustomsBase:
    id = Column(Integer, primary_key=True)


BaseModel = declarative_base(cls=CustomsBase)

ModelType = TypeVar('ModelType', bound=BaseModel)


class IpProxyModel(BaseModel):
    __tablename__ = 'ip_proxy'
    ip = Column(String(255))
    schema = Column(String(6), comment="代理 IP 的 schema")
    port = Column(Integer)

    proxy_status = relationship(
        'ProxyStatusModel',
        backref='ip_proxy',
        passive_deletes=True,
        lazy='selectin'
    )


class ProxyStatusModel(BaseModel):
    __tablename__ = 'proxy_status'
    proxy_id = Column(Integer, ForeignKey('ip_proxy.id', ondelete='CASCADE'))
    name = Column(String(255))
    alive_count = Column(Integer, comment='存活计数。可用加一，不可用减一')
    # elapse_time = Column(Integer, comment="返回响应的消耗的时间，单位 ms")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='最近一次更新时间')
