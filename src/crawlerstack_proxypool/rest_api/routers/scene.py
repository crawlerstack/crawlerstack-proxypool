"""scene route"""
from fastapi import APIRouter, Depends

from crawlerstack_proxypool.rest_api.utils import service_depend
from crawlerstack_proxypool.schema import SceneProxyUpdate
from crawlerstack_proxypool.service import SceneProxyService

router = APIRouter()


@router.get('/')
async def get(
        *,
        name: str = None,
        limit: int = 1,
        service: service_depend(SceneProxyService) = Depends(),
):
    """
    Get ip proxy
    :param name:
    :param limit:
    :param service:
    :return:
    """
    return await service.get_with_ip(
        limit=limit,
        name=name
    )


@router.put('/decrease')
async def put(
        *,
        obj_in: SceneProxyUpdate,
        service: service_depend(SceneProxyService) = Depends(),
):
    """
    decrease proxy
    :param obj_in:
    :param service:
    :return:
    """
    await service.decrease(**obj_in.dict())
