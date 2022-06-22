"""proxy repository"""


from crawlerstack_proxypool import models
from crawlerstack_proxypool.repositories.base import BaseRepository


class ProxyRepository(BaseRepository[models.ProxyModel]):
    """
    proxy
    """

    @property
    def model(self):
        return models.ProxyModel
