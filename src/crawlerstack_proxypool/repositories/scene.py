"""
scene repository
"""
from sqlalchemy import delete, select, update
from sqlalchemy.orm import contains_eager, joinedload

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.exceptions import ObjectDoesNotExist
from crawlerstack_proxypool.models import (IpModel, ProxyModel, RegionModel,
                                           SceneProxyModel)
from crawlerstack_proxypool.repositories.base import BaseRepository
from crawlerstack_proxypool.schema import CheckedProxy


class SceneProxyRepository(BaseRepository[SceneProxyModel]):
    """
    场景代理
    """

    @property
    def model(self):
        """model"""
        return SceneProxyModel

    async def get_by_names(self, names) -> list[SceneProxyModel]:
        """get by names"""
        stmt = select(
            self.model
        ).where(
            self.model.name.in_(names)
        ).options(
            joinedload(
                self.model.proxy
            ).joinedload(
                ProxyModel.ip
            )
        )

        res = await self.session.scalars(stmt)
        return res.all()

    async def update_proxy(self, obj_in: CheckedProxy) -> SceneProxyModel | None:
        """update proxy, if proxy alive count < 1, delete it."""
        protocol = obj_in.url.scheme
        port = obj_in.url.port
        ip = obj_in.url.host
        name = obj_in.name

        stmt = select(
            self.model
        ).where(
            self.model.name == name,
        ).join(
            self.model.proxy.and_(
                ProxyModel.protocol == protocol,
                ProxyModel.port == port
            )
        ).join(
            ProxyModel.ip.and_(IpModel.value == ip)
        ).options(
            contains_eager(
                self.model.proxy
            ).contains_eager(
                ProxyModel.ip
            )
        )

        obj: SceneProxyModel = await self.session.scalar(stmt)
        if obj:
            # 判断调整后对值
            alive_count = obj.alive_count + obj_in.get_alive_status()
            if alive_count > 0:
                stmt = update(self.model).where(
                    self.model.id == obj.id
                ).values(
                    {'alive_count': alive_count}
                ).execution_options(synchronize_session="fetch")
                await self.session.execute(stmt)
                return obj

            stmt = delete(self.model).where(
                self.model.id == obj.id
            ).execution_options(synchronize_session="fetch")
            await self.session.execute(stmt)

        else:
            raise ObjectDoesNotExist()

    async def get_proxy_with_region(
            self,
            /,
            limit: int = settings.DEFAULT_PAGE_LIMIT,
            offset: int = 0,
            names: list[str] = None,
            region: str | None = None,
            protocol: str | None = None,
            port: int | None = None,
            ip: str | None = None,
    ) -> list[SceneProxyModel]:
        """
        get with ip
        :param limit:
        :param offset:
        :param names:    scene names. Eg: ['http'] / ['http', 'https]
        :param protocol:    http/https/socks4/socks5
        :param region:  region code. Eg: CHN/USA
        :param port:
        :param ip:
        :return:


        在多条件 JOIN 加载数据，同时需要立即加载关联表数据时，可以使用带有急切加载的 JOIN
        https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html#joined-eager-loading
        https://docs.sqlalchemy.org/en/14/orm/internals.html#sqlalchemy.orm.PropComparator.and_

        但是在使用时会存在一个问题，暂时不知道是不是 BUG 。
        即：当多个 joinedload 级联使用当时候，第一个 joinedload 的条件会应用到后续到的 joinedload 中：

        ```python
        stmt = select(
            self.model
        ).options(
            joinedload(
                self.model.proxy.and_(ProxyModel.protocol == protocol) if protocol else self.model.proxy,
                innerjoin=True,
            ).joinedload(
                ProxyModel.ip,
                innerjoin=True,
            ).joinedload(
                IpModel.region.and_(RegionModel.code == region) if region else IpModel.region,
                innerjoin=True,
            )
        )
        ```

        生产的 SQL 是这样的：

        ```sql
        SELECT
            scene.id,
            scene.name,
            scene.alive_count,
            scene.update_time,
            scene.proxy_id,
            region_1.id AS id_1,
            region_1.name AS name_1,
            region_1.numeric,
            region_1.code,
            ip_1.id AS id_2,
            ip_1.value,
            ip_1.region_id,
            proxy_1.id AS id_3,
            proxy_1.protocol,
            proxy_1.port,
            proxy_1.ip_id
        FROM
            scene
            JOIN proxy AS proxy_1 ON proxy_1.id = scene.proxy_id
            AND proxy_1.protocol = :protocol_1
            JOIN ip AS ip_1 ON ip_1.id = proxy_1.ip_id
            AND proxy_1.protocol = :protocol_2
            JOIN region AS region_1 ON region_1.id = ip_1.region_id
            AND region_1.code = :code_1
        ```

        可以看到在 join `ip` 表的时候添加了额外的条件，这是错误的，并且当 `region` 表没有条件的时候，也会将该条件应用到这个表。

        针对这种情况就需要在 JOIN 之后使用 `contains_eager` 指定需要加载的关系即可。

        https://docs.sqlalchemy.org/en/14/orm/loading_relationships.html#routing-explicit-joins-statements-into-eagerly-loaded-collections
        """
        if not limit:
            limit = 10

        if not offset:
            offset = 0

        condition = [self.model.alive_count > 0]
        if names:
            condition.append(self.model.name.in_(names))

        proxy_and_condition = []
        if protocol:
            proxy_and_condition.append(ProxyModel.protocol == protocol)
        if port:
            proxy_and_condition.append(ProxyModel.port == port)

        stmt = select(
            self.model
        ).where(
            *condition
        ).limit(
            limit
        ).offset(
            offset
        ).order_by(
            self.model.alive_count.desc(),
            self.model.update_time.desc(),
        ).join(
            self.model.proxy.and_(*proxy_and_condition) if proxy_and_condition else self.model.proxy
        ).join(
            ProxyModel.ip.and_(IpModel.value == ip) if ip else ProxyModel.ip
        ).join(
            IpModel.region.and_(RegionModel.code == region) if region else IpModel.region
        ).options(
            contains_eager(
                self.model.proxy
            ).contains_eager(
                ProxyModel.ip,
            ).contains_eager(
                IpModel.region
            )
        )

        result = await self.session.scalars(stmt)
        scene_objs: list[SceneProxyModel] = result.all()
        data = []
        for obj in scene_objs:
            if obj.proxy is None:
                continue
            if obj.proxy.ip.region is None:
                continue
            data.append(obj)
        return data
