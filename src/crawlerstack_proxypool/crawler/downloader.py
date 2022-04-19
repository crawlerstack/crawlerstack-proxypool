import asyncio
import dataclasses
import logging

import httpx
from httpx import Response

from crawlerstack_proxypool.crawler.req_resp import RequestProxy

logger = logging.getLogger(__name__)


class DownloadHandler:
    async def download(self, request: RequestProxy) -> Response:
        """"""
        async with httpx.AsyncClient() as client:
            return await client.request(
                method=request.method,
                url=request.url,
                content=request.content,
                data=request.data,
                files=request.files,
                json=request.files,
                params=request.params,
                headers=request.headers,
                cookies=request.cookies,
                auth=request.auth,
                follow_redirects=request.follow_redirects,
            )


@dataclasses.dataclass
class Downloader:
    """"""
    loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=asyncio.get_running_loop)
    _queue: asyncio.Queue = dataclasses.field(init=False)
    handler: DownloadHandler = dataclasses.field(default_factory=DownloadHandler, init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(50)

    @property
    def queue(self):
        return self._queue

    async def enqueue(self, request) -> asyncio.Task[Response]:
        """"""
        task = self.loop.create_task(self.downloading(request))
        await self.queue.put(task)
        return task

    def idle(self) -> bool:
        logger.debug(f'Download queue size: {self.queue.qsize()}')
        return self.queue.empty()

    async def downloading(self, request):
        try:
            logger.debug(f'Start download {request}.')
            return await self.handler.download(request)
        finally:
            await self.queue.get()

    async def close(self):
        pass
