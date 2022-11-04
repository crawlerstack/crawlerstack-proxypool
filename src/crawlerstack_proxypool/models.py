from datetime import datetime
from typing import TypeVar

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import declarative_base, declared_attr, relationship


class CustomsBase:
    """
    自定义初始化规则
    """
    id = Column(Integer, primary_key=True)


BaseModel = declarative_base(cls=CustomsBase)

ModelT = TypeVar('ModelT', bound=BaseModel)


# 在父表中使用 backref 存在一个 BUG，暂时未通过 DEMO 复现，并反馈。
# 问题描述：
# 如果在子表中不设置父表的映射字段时，
# 当第一次使用 select(SceneProxyModel).options(joinedload(SceneProxyModel.ip_proxy))，
# 会提示 ip_proxy 字段找不到，如果单独先使用 select(SceneProxyModel) 查询一次，再执行上面
# 的逻辑就不会有问题。


# 注意：表索引名称要唯一，特别是主键索引不能简单设置 id_idx ，否则再 sqlite 数据库会提示索引已存在。
# 这里使用 uuid.uuid4() 的第一段 8 个字符串祖宗为索引后缀。

class RegionModel(BaseModel):
    """
    地区

    地区信息按照 ISO-3166-2 给定数据预先加载到数据库。

    注意这里是地区。不应该将香港台湾这种属于中国的地区存入该表！！！
    """
    __tablename__ = 'region'

    name = Column(String(255), comment='地区名称', nullable=False)
    numeric = Column(String(3), comment='地区三位数字码', nullable=False)
    code = Column(String(3), comment='地区三位码', nullable=False)

    ips = relationship(
        'IpModel',
        back_populates='region',
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('id_idx_6f5f1f91', 'id'),
        Index('code_idx_3a5aa32c', 'code'),
        Index('numeric_idx_f8c3b7a6', 'numeric'),
    )


class IpModel(BaseModel):
    """Ip model"""
    # TODO value 和 region 组成唯一索引
    __tablename__ = 'ip'

    value = Column(String(255), nullable=False, comment='Ip address')

    region_id = Column(Integer, ForeignKey('region.id', ondelete='CASCADE'), nullable=True)

    proxies = relationship(
        'ProxyModel',
        back_populates='ip',
        cascade="all, delete-orphan"
    )

    region = relationship('RegionModel', back_populates='ips')

    __table_args__ = (
        Index('id_idx_2bcb7644', 'id'),
        Index('value_idx_5571c34a', 'value'),
        Index('region_id_idx_9c7532be', 'region_id'),
    )


class ProxyModel(BaseModel):
    """
    代理Ip
    """
    # TODO protocol port ip 组成唯一索引
    __tablename__ = 'proxy'

    protocol = Column(String(6), comment='代理 IP 的 protocol', nullable=False)
    port = Column(Integer, nullable=False)

    ip_id = Column(Integer, ForeignKey('ip.id', ondelete='CASCADE'), nullable=False)

    scenes = relationship(
        'SceneProxyModel',
        back_populates='proxy',
        cascade="all, delete-orphan"
    )

    ip = relationship('IpModel', back_populates='proxies')

    __table_args__ = (
        Index('id_idx_0aa99d16', 'id'),
        Index('ip_id_idx_9160aafd', 'ip_id'),
    )


class SceneProxyModel(BaseModel):
    """
    场景模型
    """
    # TODO proxy 和 name 组成唯一索引
    __tablename__ = 'scene'
    name = Column(String(255), nullable=False)
    alive_count = Column(Integer, comment='存活计数。可用加一，不可用减一', nullable=False)
    # elapse_time = Column(Integer, comment="返回响应的消耗的时间，单位 ms")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='最近一次更新时间',
                         nullable=False)

    proxy_id = Column(Integer, ForeignKey('proxy.id', ondelete='CASCADE'), nullable=False)

    proxy = relationship('ProxyModel', back_populates="scenes")

    __table_args__ = (
        Index('id_idx_83a604b6', 'id'),
        Index('name_idx_e755c362', 'name'),
        Index('proxy_id_idx_30b08a16', 'proxy_id'),
    )
