"""TestSpider"""
import logging

import pytest
from redis import Redis
from scrapy import Request
from scrapy.exceptions import DontCloseSpider

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core.spiders import RedisSpider


class DemoRedisSpider(RedisSpider):
    """Demo spider to test"""
    name = 'demo'

    def parse(self, response, **kwargs):
        """parse"""


@pytest.mark.parametrize(
    'redis_batch_size',
    [None, 1]
)
def test__setup_redis(get_crawler, mocker, redis_batch_size):
    """test _setup_redis method"""
    from_url_mocker = mocker.patch.object(Redis, 'from_url')
    customs_settings = {
        'REDIS_START_URL_BATCH_SIZE': redis_batch_size,
    }

    crawler = get_crawler(**customs_settings)

    spider = DemoRedisSpider.from_crawler(crawler)
    if redis_batch_size:
        assert spider.redis_batch_size == redis_batch_size
    else:
        assert spider.redis_batch_size == settings.CONCURRENT_REQUESTS

    from_url_mocker.assert_called()


def test__setup_redis_has_server(get_crawler, mocker):
    """test _setup_redis method when pass a server"""
    mock_server = mocker.MagicMock()
    spider = DemoRedisSpider.from_crawler(get_crawler(), server=mock_server)
    assert mock_server is spider.server


def test__setup_redis_error():
    """test _setup_redis error"""
    with pytest.raises(AttributeError):
        spider = DemoRedisSpider()
        spider._setup_redis()  # pylint: disable=protected-access


@pytest.mark.parametrize(
    'use_set',
    [True, False]
)
def test(get_crawler, mocker, use_set):
    """test spider logic"""
    batch_size = 5
    mock_redis = mocker.MagicMock()
    mocker.patch.object(Redis, 'from_url', return_value=mock_redis)

    mock_request_cls = mocker.patch('scrapy.spiders.Request', mocker.MagicMock)

    urls = []
    requests = []
    for i in range(batch_size + 1):
        url = f'http://example.com/{i}'
        urls.append(url)
        requests.append(mock_request_cls(url))

    def fetch_one(_name: str):
        if urls:
            return urls.pop()
        return None

    if use_set:
        mock_redis.spop = mocker.MagicMock(side_effect=fetch_one)
    else:
        mock_redis.lpop = mocker.MagicMock(side_effect=fetch_one)

    crawler = get_crawler(**{
        'REDIS_START_URL_AS_SET': use_set,
        'REDIS_START_URL_BATCH_SIZE': batch_size,
        # 'REDIS_URL': 'redis://127.0.0.1:6379/2',
    })
    mock_crawler = mocker.MagicMock(spec=crawler, settings=crawler.settings)
    spider = DemoRedisSpider.from_crawler(mock_crawler)

    assert len(requests[:batch_size]) == len(list(spider.start_requests()))

    with pytest.raises(DontCloseSpider):
        spider.spider_idle()

    spider.crawler.engine.crawl.assert_called()


def test_requests_no_request(get_crawler, mocker, caplog):
    """test requests no request"""
    batch_size = 1
    customs_settings = {
        'REDIS_START_URL_AS_SET': True,
        'REDIS_START_URL_BATCH_SIZE': batch_size,
    }

    class FakeSpider(RedisSpider):
        """Demo spider to test"""
        name = 'fake'
        count = 0

        def parse(self, response, **kwargs):
            """imp parse"""

        def make_request_from_url(self, url: str):
            """override"""
            resp = None
            if self.count == self.redis_batch_size:
                resp = Request(url)
            self.count += 1
            return resp

    mock_redis = mocker.MagicMock()
    mocker.patch.object(Redis, 'from_url', return_value=mock_redis)
    mock_redis.spop = mocker.MagicMock(side_effect=['http://example.com', 'http://example.com'])

    spider = FakeSpider.from_crawler(get_crawler(**customs_settings))
    with caplog.at_level(level=logging.DEBUG):
        assert len(list(spider.start_requests())) == batch_size
        assert 'Request not made from data:' in caplog.text
