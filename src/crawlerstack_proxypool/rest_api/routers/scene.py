"""scene route"""
from typing import List

from fastapi import APIRouter, Depends

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.rest_api.utils import service_depend
from crawlerstack_proxypool.schema import (SceneIpProxyCreate,
                                           SceneIpProxyMessage)
from crawlerstack_proxypool.service import SceneProxyService

router = APIRouter()


@router.get('/', response_model=List[SceneIpProxyMessage])
async def get(
        *,
        name: str = None,
        limit: int = settings.DEFAULT_PAGE_LIMIT,
        service: service_depend(SceneProxyService) = Depends(),
):
    """
    Get ip proxy
    :param name:
    :param limit:
    :param service:
    :return:
    """
    return await service.get_with_region(
        limit=limit,
        names=[name]
    )


@router.put('/decrease')
async def put(
        *,
        obj_in: SceneIpProxyCreate,
        service: service_depend(SceneProxyService) = Depends(),
):
    """
    decrease proxy
    :param obj_in:
    :param service:
    :return:
    """
    await service.decrease(obj_in)
