from aiohttp import ClientRequest


class CrawlerStackProxyPoolError(Exception):
    """"""


class SpiderError(CrawlerStackProxyPoolError):
    """"""


class SpiderRequestError(CrawlerStackProxyPoolError):

    def __init__(self, request: ClientRequest, exception):
        self._request = request
        self.exception = exception

    def __str__(self):
        return f'Request url {self._request.url} with proxies {self._request.proxy} error. {self.exception}'


class MaxRetryError(SpiderError):
    """"""


class ObjectDoesNotExist(CrawlerStackProxyPoolError):
    """"""
