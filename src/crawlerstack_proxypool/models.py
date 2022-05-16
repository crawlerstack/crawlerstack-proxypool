from datetime import datetime
from typing import TypeVar

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship


class CustomsBase:
    """
    自定义初始化规则
    """
    id = Column(Integer, primary_key=True)


BaseModel = declarative_base(cls=CustomsBase)

ModelT = TypeVar('ModelT', bound=BaseModel)


class IpProxyModel(BaseModel):
    """
    Ip 代理
    """
    __tablename__ = 'ip_proxy'
    ip = Column(String(255))
    protocol = Column(String(6), comment="代理 IP 的 schema")
    port = Column(Integer)

    scenes = relationship(
        'SceneProxyModel',
        back_populates='ip_proxy',
        cascade="all, delete-orphan"
        # passive_deletes=True,
        # lazy='selectin'
    )


class SceneProxyModel(BaseModel):
    """
    场景模型
    """
    __tablename__ = 'scene_proxy'
    proxy_id = Column(Integer, ForeignKey('ip_proxy.id', ondelete='CASCADE'))
    name = Column(String(255))
    alive_count = Column(Integer, comment='存活计数。可用加一，不可用减一')
    # elapse_time = Column(Integer, comment="返回响应的消耗的时间，单位 ms")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='最近一次更新时间')

    # 在父表中使用 backref 存在一个 BUG，暂时未通过 DEMO 复现，并反馈。
    # 问题描述：
    # 如果在子表中不设置父表的映射字段时，
    # 当第一次使用 select(SceneProxyModel).options(joinedload(SceneProxyModel.ip_proxy))，
    # 会提示 ip_proxy 字段找不到，如果单独先使用 select(SceneProxyModel) 查询一次，再执行上面
    # 的逻辑就不会有问题。
    ip_proxy = relationship('IpProxyModel', back_populates="scenes")
