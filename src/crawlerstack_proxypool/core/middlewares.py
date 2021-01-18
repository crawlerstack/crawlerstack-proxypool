"""Scrapy middleware"""
import random
import time
from typing import Optional

from fake_useragent import UserAgent
from scrapy.exceptions import NotConfigured

from crawlerstack_proxypool.core.base import BaseSpider


class UserAgentMiddleware(object):
    """Add random ua to request."""

    def __init__(self):
        self.ua = UserAgent()

    def process_request(self, request, spider):
        """Add ua"""
        ua = self.ua.random
        spider.logger.debug(f'{request.url} ua: {ua}')
        request.headers.setdefault(b'User-Agent', ua)


class ProxyMiddleware(object):
    """Add proxy to request."""
    gfw_proxy: str = None

    @classmethod
    def from_crawler(cls, crawler):
        obj = cls()
        if not crawler.settings.get('GFW_PROXY'):
            raise NotConfigured('GFW_PROXY not config!')
        obj.gfw_proxy = crawler.settings.get('GFW_PROXY')
        return obj

    def _fetch_local_proxy(self, spider: BaseSpider) -> Optional[str]:
        """
        :param spider:
        :return:    'http' / None
        """
        proxy = None
        if hasattr(spider, 'gfw') and spider.gfw:
            proxy = self.gfw_proxy
        else:
            if random.randint(0, 9) % 2:
                proxy = self.gfw_proxy
        return proxy

    def process_request(self, request, spider):
        """
        :param request:
        :param spider:
        :return:
        """
        if 'scene' not in request.meta:
            proxy = self._fetch_local_proxy(spider)

            if proxy:
                if 'splash' in request.meta:
                    request.meta['splash']['args']['proxy'] = proxy
                    debug_info = f'{request.url} splash proxy: "{proxy}"'
                else:
                    request.meta['proxy'] = proxy
                    debug_info = f'{request.url} proxy: "{proxy}"'
            else:
                debug_info = f'No proxy to use in {request.url} , random not set.'
            spider.logger.debug(debug_info)


class RequestProfileMiddleware(object):
    """This middleware calculates the ip's speed"""

    def process_request(self, request, spider):
        request.meta['start'] = time.time()

    def process_response(self, request, response, spider):
        end = time.time()
        speed = end - request.meta['start']
        request.meta['speed'] = int(speed * 1000)
        return response

    def process_exception(self, request, exception, spider):
        end = time.time()
        speed = end - request.meta['start']
        request.meta['speed'] = int(speed * 1000)
