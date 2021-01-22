"""Scrapy middleware"""
import random
import time
from typing import Optional

from fake_useragent import UserAgent
from scrapy.exceptions import NotConfigured

from crawlerstack_proxypool.core.base import BaseSpider


class UserAgentMiddleware:  # pylint: disable=too-few-public-methods
    """Add random ua to request."""

    def __init__(self):
        self.user_agent = UserAgent()

    def process_request(self, request, spider):
        """Add ua"""
        user_agent = self.user_agent.random
        spider.logger.debug(f'{request.url} ua: {user_agent}')
        request.headers.setdefault(b'User-Agent', user_agent)


class ProxyMiddleware:
    """Add proxy to request."""
    gfw_proxy: str = None

    @classmethod
    def from_crawler(cls, crawler):
        """Init obj from crawler"""
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


class RequestProfileMiddleware:
    """This middleware calculates the ip's speed"""

    def process_request(self, request, spider):  # pylint: disable=no-self-use
        """Process request"""
        del spider  # no use
        request.meta['start'] = time.time()

    def process_response(self, request, response, spider):  # pylint: disable=no-self-use
        """Process response"""
        del spider  # no use
        end = time.time()
        speed = end - request.meta['start']
        request.meta['speed'] = int(speed * 1000)
        return response

    def process_exception(self, request, exception, spider):  # pylint: disable=no-self-use
        """Process exception"""
        del exception, spider  # no use
        end = time.time()
        speed = end - request.meta['start']
        request.meta['speed'] = int(speed * 1000)
