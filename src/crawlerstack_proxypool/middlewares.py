"""middleware"""
import logging

import httpx

from crawlerstack_proxypool.aio_scrapy.middlewares import DownloadMiddleware

logger = logging.getLogger(__name__)


class ExceptionMiddleware(DownloadMiddleware):
    """Exception middleware"""
    async def process_exception(self, exception, request, spider):
        """process exception"""
        if isinstance(exception, httpx.ConnectError):
            logging.warning('httpx.ConnectError, url: %s, proxy: %s',request.url, request.proxy)
            return
        return exception
