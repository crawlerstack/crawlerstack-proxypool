from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from crawlerstack_proxypool.db import Base


class IpAddressModel(Base):
    __tablename__ = 'ip_address'
    ip = Column(String(255))

    ip_proxies = relationship(
        'IpProxy',
        backref='ip_address',
        passive_deletes=True
    )


class IpProxyModel(Base):
    __tablename__ = 'ip_proxy'
    ip_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"))
    schema = Column(String(6), comment="代理 IP 的 schema")
    port = Column(Integer)
    anonymous = Column(Integer, comment="代理匿名。可用值 0, 1, 2 。")

    proxy_status = relationship(
        'ProxyStatusModel',
        backref='ip_proxy',
        passive_deletes=True
    )


class ProxyStatusModel(Base):
    __tablename__ = 'proxy_status'
    proxy_id = Column(Integer, ForeignKey('ip_proxy.id', ondelete='CASCADE'))
    name = Column(String(255))
    alive_count = Column(Integer, comment="存活计数。可用加一，不可用减一。")
    elapse_time = Column(Integer, comment="返回响应的消耗的时间，单位 ms")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="最近一次更新时间")
