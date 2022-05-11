"""
exception
"""
from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy


class CrawlerStackProxyPoolError(Exception):
    """
    异常基类
    """


class SpiderError(CrawlerStackProxyPoolError):
    """
    spider error
    """


class SpiderRequestError(CrawlerStackProxyPoolError):
    """
    spider request error
    """

    def __init__(self, request: RequestProxy, exception):
        self._request = request
        self.exception = exception

    def __str__(self):
        return f'Request url {self._request.url} with proxies {self._request.proxy} error. {self.exception}'


class MaxRetryError(SpiderError):
    """
    max retry error
    """


class ObjectDoesNotExist(CrawlerStackProxyPoolError):
    """
    object does not exist.
    """
