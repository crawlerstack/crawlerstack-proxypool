"""
下载处理。

封装真正下载逻辑的地方。
"""

import dataclasses
import typing

from aiohttp import ClientSession

from crawlerstack_proxypool.crawler.req_resp import RequestProxy, ResponseProxy

if typing.TYPE_CHECKING:
    from crawlerstack_proxypool.crawler.spider import Spider


@dataclasses.dataclass
class DownloadHandler:
    spider: 'Spider'
    # TODO 增加并发控制
    _session: ClientSession = dataclasses.field(default_factory=ClientSession, init=False)

    @property
    def logger(self):
        """
        获取 spider 的 logger 对象。
        :return:
        """
        return self.spider.logger

    async def downloading(self, request: RequestProxy) -> ResponseProxy | Exception:
        """
        下载处理器，真正下载的逻辑。
        :param request:
        :return:
        """
        try:
            self.logger.debug(f'Downloading <{request}>')
            async with self._session.request(**request.__dict__) as client_response:
                response = await ResponseProxy.from_client_response(response=client_response, request=request)
                self.logger.debug(f'Downloaded <{response}>.')
                return response
        except Exception as ex:
            self.logger.debug(f'Download error with <{request}>')
            self.logger.exception(ex)
            return ex

    async def close(self, **_kwargs):
        """
        手动关闭 session
        :return:
        """
        await self._session.close()
