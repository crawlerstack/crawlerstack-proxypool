"""routers"""
from fastapi import APIRouter, FastAPI

from crawlerstack_proxypool.rest_api.routers import scene


def router_v1():
    """v1 router"""
    router = APIRouter()

    router.include_router(scene.router, tags=['scene'], prefix='/scenes')

    return router


def init_route(app: FastAPI):
    """init route"""
    app.include_router(router_v1(), prefix='/api/v1')
