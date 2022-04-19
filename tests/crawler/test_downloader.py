import pytest

from crawlerstack_proxypool.crawler.downloader import Downloader, DownloadHandler


@pytest.fixture()
async def downloader():
    yield Downloader()


@pytest.mark.asyncio
async def test_downloader(mocker, downloader):
    download = mocker.patch.object(DownloadHandler, 'download')
    download_task = await downloader.enqueue(mocker.MagicMock())
    await download_task
    assert downloader.queue.empty()
    download.assert_called_once()
