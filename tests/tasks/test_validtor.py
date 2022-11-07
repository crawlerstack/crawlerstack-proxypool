"""test validator"""

import pytest
from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.common import BaseParser
from crawlerstack_proxypool.common.validator import ValidatedProxy
from crawlerstack_proxypool.service import ValidateSpiderService
from crawlerstack_proxypool.tasks.validator import ValidateSpiderTask


class MockExtractor(BaseParser):
    """Mock extractor"""

    async def parse(self, response: Response, **kwargs):
        pass


@pytest.mark.asyncio
async def test_validate_spider_task(mocker):
    """test validate spider task"""
    name = 'foo'
    dest = ['dest']
    source = 'foo'
    check_urls = ['https://example.com']
    exist_proxies = ['http://127.0.0.1:1080']
    checked_data = ValidatedProxy(
        url=URL(exist_proxies[0]),
        name=name,
        source=source,
        dest=dest,
        alive=True
    )

    mocker.patch.object(MockExtractor, 'parse', return_value=checked_data)
    download_mocker = mocker.patch.object(DownloadHandler, 'download')
    save_mocker = mocker.patch.object(ValidateSpiderService, 'init_proxy')
    mocker.patch.object(ValidateSpiderService, 'get_proxies', return_value=exist_proxies)

    task = ValidateSpiderTask(
        name=name,
        original=True,
        check_urls=check_urls,
        parser_kls=MockExtractor,
        source=source,
        dest=dest,
    )
    await task.start()

    save_mocker.assert_called_once_with(checked_data)
    download_mocker.assert_called_once()
