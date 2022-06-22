"""
ip repository
"""
from crawlerstack_proxypool import models
from crawlerstack_proxypool.repositories.base import BaseRepository


class IpRepository(BaseRepository[models.IpModel]):
    """
    ip
    """

    @property
    def model(self):
        return models.IpModel
