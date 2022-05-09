import typing

from httpx import URL, Response

from crawlerstack_proxypool.crawler.req_resp import RequestProxy


class Spider:
    """"""

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str],
            **kwargs,
    ):
        self.name = name
        self.start_urls = start_urls
        for k, v in kwargs.items():
            setattr(self, k, v)

    def start_requests(self) -> typing.Iterator[RequestProxy]:
        """
        起始 requests
        :return:
        """
        for i in self.start_urls:
            yield self._make_request(i)

    def _make_request(self, url: URL | str) -> RequestProxy:  # noqa
        """
        构建请求
        :param url:
        :return:
        """
        req = RequestProxy(method='GET', url=url)
        return req

    async def parse(self, response: Response) -> typing.Any:
        """
        解析逻辑
        :param response:
        :return:
        """
        raise NotImplementedError()
