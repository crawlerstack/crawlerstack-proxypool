from fastapi import APIRouter, FastAPI

from crawlerstack_proxypool.rest_api.routers import ip_proxy


def router_v1():
    router = APIRouter()

    router.include_router(ip_proxy.router, tags=['ip_proxy'], prefix='/ip_proxies')

    return router


def init_route(app: FastAPI):
    app.include_router(router_v1(), prefix='/api/v1')
