"""
下载器
"""
import asyncio
import dataclasses
import logging

import httpx
from httpx import Response

from crawlerstack_proxypool.crawler.req_resp import RequestProxy

logger = logging.getLogger(__name__)


class BaseDownloadHandler:
    """
    下载处理抽象类
    """

    async def download(self, request: RequestProxy) -> Response:
        """
        下载
        :param request:
        :return:
        """
        raise NotImplementedError()

    async def close(self):
        """
        关闭
        :return:
        """
        raise NotImplementedError()


class DownloadHandler(BaseDownloadHandler):
    """
    下载处理类，封装下载库
    """

    async def download(self, request: RequestProxy) -> Response:
        """
        下载
        :param request:
        :return:
        """
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

    async def close(self):
        pass


@dataclasses.dataclass
class Downloader:
    """
    下载器，使用队列异步处理下载任务
    """
    loop: asyncio.AbstractEventLoop = dataclasses.field(default_factory=asyncio.get_running_loop)
    _queue: asyncio.Queue = dataclasses.field(init=False)
    handler: DownloadHandler = dataclasses.field(default_factory=DownloadHandler, init=False)

    def __post_init__(self):
        self._queue = asyncio.Queue(5)

    @property
    def queue(self):
        """
        获取队列
        :return:
        """
        return self._queue

    async def enqueue(self, request) -> asyncio.Task[Response]:
        """
        将请求构建下载任务然后放入队列
        :param request:
        :return:
        """
        logger.debug('Enqueue request: %s', request)
        await self.queue.put(request)
        logger.debug('Current downloader queue size: %d, enqueued request: %s', self.queue.qsize(), request)
        task = self.loop.create_task(self.downloading(request))
        return task

    def should_pass(self) -> bool:
        """
        判断是否需要跳过
        :return:
        """
        return self.queue.full()

    def idle(self) -> bool:
        """
        下载器是否空闲
        :return:
        """
        return self.queue.empty()

    async def downloading(self, request) -> Response | None:
        """
        下载中
        :param request:
        :return:
        """
        try:
            resp = await self.handler.download(request)
            logger.debug('Downloaded request %s.', request)
            return resp
        except Exception as ex:
            logger.error(ex)
            # 增加异常处理逻辑
        finally:
            await self.queue.get()

    async def close(self):
        """
        关闭下载
        :return:
        """
