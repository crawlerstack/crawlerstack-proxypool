import pytest

from crawlerstack_proxypool.aio_scrapy.scraper import Scraper


@pytest.fixture()
async def scraper():
    yield Scraper()


@pytest.mark.asyncio
async def test_scrape(mocker, scraper):
    spider = mocker.AsyncMock()
    scrap_task = await scraper.enqueue(mocker.MagicMock(), spider)
    await scrap_task
    assert scraper.queue.empty()
    spider.parse.assert_called_once()
