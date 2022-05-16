"""middleware"""
import abc
import asyncio
import logging
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Generic, TypeVar

from httpx import Response

from crawlerstack_proxypool.aio_scrapy.settings import Settings

logger = logging.getLogger(__name__)


class BaseExtension:

    def open_spider(self, spider):
        """open spider"""

    def close_spider(self, spider):
        """close spider"""


class BaseMiddleware:
    """
    Base middleware
    """

    async def process_exception(self, exception, request, spider):
        """process exception"""


class BaseSpiderMiddleware(BaseMiddleware):
    """
    Spider middleware
    """

    async def process_input(self, request, spider):
        """
        process spider input
        :param request:
        :param spider:
        :return:
        """

    async def process_output(self, output, request, spider):
        """
        process spider output
        :param output:
        :param request:
        :param spider:
        :return:
        """


class DownloadMiddleware(BaseMiddleware):
    """
    Download middleware
    """

    async def process_request(self, request, spider):
        """
        process request
        :param request:
        :param spider:
        :return:
        """

    async def process_response(self, response, request, spider):
        """
        process response
        :param response:
        :param request:
        :param spider:
        :return:
        """


MiddlewareType = TypeVar('MiddlewareType', bound=BaseMiddleware)


async def _process_parallel(methods, *args):
    """process parallel"""
    return await asyncio.gather(*[method(*args) for method in methods])


class MiddlewareManager(Generic[MiddlewareType]):
    """Base middleware manager"""
    NAME: str

    def __init__(self, mws: list[MiddlewareType]):
        self.methods: dict[str, deque[Callable]] = defaultdict(deque)
        self._add_mws(mws)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        from settings
        :param settings:
        :return:
        """
        mws_kls = cls._get_mws_kls(settings)
        mws = []
        for mw_kls in mws_kls:
            mws.append(mw_kls())
        logger.info('Enable %s: %s', cls.NAME, mws_kls)
        return cls(mws)

    @classmethod
    @abc.abstractmethod
    def _get_mws_kls(cls, settings: Settings):
        raise NotImplementedError()

    def _add_mws(self, mws: list[MiddlewareType]):
        for middleware in mws:
            if getattr(middleware, 'open_spider'):
                self.methods['open_spider'].append(middleware.open_spider)
            if getattr(middleware, 'close_spider'):
                self.methods['close_spider'].append(middleware.close_spider)

    async def process_exception(self, exception, request, spider):
        """
        process exception
        :param exception:
        :param request:
        :param spider:
        :return:
        """
        for method in self.methods['process_exception']:
            await method(exception, request, spider)
        raise exception


class DownloadMiddlewareManager(MiddlewareManager[DownloadMiddleware]):
    """
    Download middleware manager
    """
    NAME: str = 'DownloadMiddleware'

    @classmethod
    def _get_mws_kls(cls, settings: Settings):
        return settings.download_middlewares

    def _add_mws(self, mws: list[MiddlewareType]):
        for middleware in mws:
            if getattr(middleware, 'process_request'):
                self.methods['process_request'].append(middleware.process_request)
            if getattr(middleware, 'process_response'):
                self.methods['process_response'].appendleft(middleware.process_response)
            if getattr(middleware, 'process_exception'):
                self.methods['process_exception'].appendleft(middleware.process_exception)

    async def download(self, download_func, request, spider):
        """download"""
        try:
            response = await self.process_request(request, spider)
            if isinstance(response, Response):
                return response
            response = await download_func(request=request, spider=spider)
        except Exception as ex:
            return await self.process_exception(ex, request, spider)

        return await self.process_response(response, request, spider)

    async def process_request(self, request, spider):
        """
        process request
        :param request:
        :param spider:
        :return:
        """
        for method in self.methods['process_request']:
            await method(request, spider)

    async def process_response(self, response, request, spider):
        """
        process response
        :param response:
        :param request:
        :param spider:
        :return:
        """
        for method in self.methods['process_response']:
            response = await method(response, request, spider)
        return response


class SpiderMiddlewareManager(MiddlewareManager[BaseSpiderMiddleware]):
    """
    Spider middleware manager

    TODO impl
    """
    NAME: str = 'SpiderMiddleware'

    @classmethod
    def _get_mws_kls(cls, settings: Settings):
        pass

    def _add_mws(self, mws: list[MiddlewareType]):
        for middleware in mws:
            if getattr(middleware, 'process_input'):
                self.methods['process_input'].append(middleware.process_input)
            if getattr(middleware, 'process_output'):
                self.methods['process_output'].appendleft(middleware.process_output)
