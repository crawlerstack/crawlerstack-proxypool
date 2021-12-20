from crawlerstack_proxypool.repositories import BaseRepository


class BaseService:

    def __init__(self, repository: BaseRepository):
        self._repository = repository

    def get_all(self):
        return self._repository.get_all()

    def get_by_id(self, pk: int):
        return self._repository.get_by_id(pk)

    def create(self, **kwargs):
        return self._repository.create(**kwargs)


class IpProxyService(BaseService):
    """"""
