"""
scene repository
"""
from sqlalchemy import select
from sqlalchemy.orm import joinedload, subqueryload, defaultload, selectinload

from crawlerstack_proxypool.models import SceneProxyModel, ProxyModel, IpModel, RegionModel
from crawlerstack_proxypool.repositories.base import BaseRepository
from crawlerstack_proxypool.schema import SceneIpProxy, SceneIpProxyWithRegion


class SceneProxyRepository(BaseRepository[SceneProxyModel]):
    """
    场景代理
    """

    @property
    def model(self):
        """model"""
        return SceneProxyModel

    async def get_proxy_with_region(
            self,
            /,
            limit: int = 10,
            offset: int = 0,
            names: list[str] = None,
            protocol: str | None = None,
            region: str | None = None,
    ) -> list[SceneIpProxyWithRegion]:
        """
        get with ip
        :param limit:
        :param offset:
        :param names:    scene names. Eg: ['http'] / ['http', 'https]
        :param protocol:    http/https/socks4/socks5
        :param region:  region code. Eg: CHN/USA
        :return:
        """
        # 将其他表的过滤条件放在 JOIN 中
        # https://docs.sqlalchemy.org/en/14/orm/internals.html#sqlalchemy.orm.PropComparator.and_
        # 使用时遇到个 BUG，即再使用 joinedload 做链式 JOIN 时，
        # 如果第一个 JOIN 时使用了 and_ 条件，该条件会一并出现在后续所有的 JOIN 中。

        if not limit:
            limit = 10

        if not offset:
            offset = 0

        condition = []
        if names:
            condition.append(self.model.name.in_(names))
        # if protocol:
        #     condition.append(ProxyModel.protocol == protocol)
        # if region:
        #     condition.append(RegionModel.code == region)

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
        ).options(
            # 这里使用 selectinload 使用急切加载
            # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession
            selectinload(
                # 使用 and 条件
                # https://docs.sqlalchemy.org/en/14/orm/queryguide.html#augmenting-built-in-on-clauses
                self.model.proxy.and_(ProxyModel.protocol == protocol) if protocol else self.model.proxy
            ).selectinload(
                ProxyModel.ip
            ).selectinload(
                IpModel.region.and_(RegionModel.code == region) if region else IpModel.region
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
            data.append(SceneIpProxyWithRegion(
                name=obj.name,
                ip=obj.proxy.ip.value,
                port=obj.proxy.port,
                protocol=obj.proxy.protocol,
                region=obj.proxy.ip.region.code
            ))
        return data
