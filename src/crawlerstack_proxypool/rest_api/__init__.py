"""rest api server"""
import dataclasses

from fastapi import FastAPI
from uvicorn import Config, Server

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.rest_api.routers import init_route


@dataclasses.dataclass
class RestAPI:
    """
    Rest api
    """
    db: Database
    port: int | None = 8000
    host: str | None = '127.0.0.1'

    _app: FastAPI = dataclasses.field(init=False)
    _uvicorn_server: Server = dataclasses.field(init=False)

    def __post_init__(self):
        self._app = FastAPI(
            db=self.db
        )

        uvicorn_config = Config(self._app, host=self.host, port=self.port)
        self._uvicorn_server = Server(uvicorn_config)

    @property
    def app(self):
        """app"""
        return self._app

    def init(self):
        """Init rest api"""
        init_route(self._app)

    async def _uvicorn_server_setup(self):
        config = self._uvicorn_server.config
        if not config.loaded:
            config.load()

        self._uvicorn_server.lifespan = config.lifespan_class(config)
        await self._uvicorn_server.startup()

    async def start(self) -> None:
        """start server"""
        await self._uvicorn_server_setup()

    async def stop(self) -> None:
        """Stop server"""
        # 由于 _uvicorn_server 是在 startup 是初始化 servers 属性的，
        # 所以在测试时，如果不运行 self.start 逻辑， _uvicorn_server.shutdown
        # 会报错
        if hasattr(self._uvicorn_server, 'servers'):
            await self._uvicorn_server.shutdown()

    async def restart(self) -> None:
        """restart server"""
