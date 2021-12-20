import asyncio
import logging
from collections import AsyncIterator
from contextlib import AbstractAsyncContextManager

from aiohttp import ClientResponse, hdrs, ClientSession, ClientError

logger = logging.getLogger(__name__)


# class BaseSpider:
#     start_urls = []
#     max_retry = 2
#
#     def __init__(self):
#         self._session = ClientSession()
#         self._queue = asyncio.Queue()
#
#     async def start_request(self) -> AsyncIterator[AbstractAsyncContextManager[ClientResponse]]:
#         for i in self.start_urls:
#             yield self.make_request(url=i)
#
#     def make_request(self, url: str) -> AbstractAsyncContextManager[ClientResponse]:
#         return self._session.request(method=hdrs.METH_GET, url=url)
#
#     async def parse(self, response: ClientResponse):
#         raise NotImplementedError()
#
#     async def run(self) -> None:
#         async for req_ctx in self.start_request():
#             data = await self.download(req_ctx)
#
#             await self.pipeline(data)
#
#     async def download(self, request_ctx: AbstractAsyncContextManager[ClientResponse]) -> dict:
#         """
#         Download, and try
#         :param request_ctx:
#         :return:
#         """
#         ex = None
#         for i in range(self.max_retry):
#             try:
#                 async with request_ctx as response:
#                     return await self.parse(response)
#             except ClientError as ex:
#                 logger.error(ex)
#         raise Exception(f'Max retry to request.') from ex
#
#     async def pipeline(self, item: dict):
#         """"""


# class DemoSpider(BaseSpider):
#     """"""
#
#     async def parse(self, response: ClientResponse):
#         pass


if __name__ == '__main__':
    """"""
