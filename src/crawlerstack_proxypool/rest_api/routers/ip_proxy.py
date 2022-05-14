from fastapi import APIRouter, Query, Depends
from fastapi import Response

from crawlerstack_proxypool.rest_api.utils import service_depend
from crawlerstack_proxypool.service import IpProxyService

router = APIRouter()


@router.get('/')
async def get(
        *,
        usage: str = None,
        limit: int = 1,
        service: service_depend(IpProxyService) = Depends(),
):
    """
    Get ip proxy
    :param usage:
    :param limit:
    :param service:
    :return:
    """

    return await service.get(
        limit=limit,
        usage=usage
    )


@router.put('/decrease')
async def put()
