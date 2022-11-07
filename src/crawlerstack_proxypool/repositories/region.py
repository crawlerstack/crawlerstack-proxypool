"""
region repository
"""
from crawlerstack_proxypool import models
from crawlerstack_proxypool.repositories.base import BaseRepository


class RegionRepository(BaseRepository[models.RegionModel]):
    """Region"""

    @property
    def model(self):
        return models.RegionModel
