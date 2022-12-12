"""middleware"""
import logging

import httpx

from crawlerstack_proxypool.aio_scrapy.middlewares import DownloadMiddleware

logger = logging.getLogger(__name__)


class ExceptionMiddleware(DownloadMiddleware):
    """Exception middleware"""
    exception_category = {
        'httpx.ConnectError': httpx.ConnectError,
        'httpx.ConnectTimeout': httpx.ConnectTimeout,
        'httpx.ReadTimeout': httpx.ReadTimeout,
        'httpx.RemoteProtocolError': httpx.RemoteProtocolError,
        'httpx.ReadError': httpx.ReadError,
        'httpx.ProxyError': httpx.ProxyError
    }

    async def process_exception(self, exception, request, spider):
        """process exception"""
        for k, v in self.exception_category.items():
            if isinstance(exception, v):
                logging.warning('%s, url: %s, proxy: %s', k, request.url, request.proxy)
                return
        return exception
