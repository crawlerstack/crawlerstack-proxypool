import typing
from typing import Any

from crawlerstack_proxypool.crawler.req_resp import ResponseProxy

if typing.TYPE_CHECKING:
    from crawlerstack_proxypool.crawler.spider import Spider


class BaseParser:

    def __init__(self, spider: 'Spider'):
        self.spider = spider

    async def parse(self, response: ResponseProxy, **kwargs):
        """
        解析 response 。此方法必须是异步方法。
        :param response:
        :return:
        """
        raise NotImplementedError()


class DefaultParser(BaseParser):

    async def parse(self, response: ResponseProxy, **_kwargs) -> Any:
        """
        解析 response
        :param response:
        :param _kwargs:
        :return:
        """
        result = {
            'url': response.url,
            'text': response.text,
            'status_code': response.status
        }
        self.spider.logger.debug(f'Parsed result {result}')
        return result
