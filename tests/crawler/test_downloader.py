"""Test downloader"""
import pytest

from crawlerstack_proxypool.crawler.downloader import Downloader, DownloadHandler
from crawlerstack_proxypool.crawler.req_resp import RequestProxy


@pytest.fixture()
async def downloader():
    """downloader fixture"""
    yield Downloader()


@pytest.fixture()
async def download_handler():
    """download_handler fixture"""
    yield DownloadHandler()


@pytest.mark.asyncio
async def test_downloader(mocker, downloader):
    """test download"""
    download = mocker.patch.object(DownloadHandler, 'download')
    download_task = await downloader.enqueue(mocker.MagicMock())
    await download_task
    assert downloader.queue.empty()
    download.assert_called_once()


@pytest.mark.asyncio
async def test_download_handler(mocker, download_handler):
    """test download_handler"""
    request = RequestProxy('GET', 'https://httpbin.iclouds.work/ip')
    resp = await download_handler.download(request)
    assert resp.status_code == 200
