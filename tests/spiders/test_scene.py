"""Test scene spider"""
import pytest
import pytest_twisted
from redis import Redis
from scrapy import Request, signals
from scrapy.crawler import CrawlerRunner

from crawlerstack_proxypool.core.schemas import SceneTaskSchema
from crawlerstack_proxypool.spiders.scene import SceneSpider


def test_setup_plugin(crawler):
    """Test setup plugin"""
    spider = SceneSpider.from_crawler(crawler, 'foo')
    assert spider.checker


@pytest.mark.parametrize(
    'from_redis, expect_value',
    [
        (False, 'http://httpbin.org/ip'),
        (True, 'http://example.com')
    ]
)
def test_random_verification_url(
        mocker,
        settings_dict,
        crawler_factory,
        from_redis,
        expect_value
):
    """Test random verification url"""
    mocker.patch.object(
        Redis,
        'execute_command',
        return_value=expect_value
    )
    scene_task = SceneTaskSchema(
        name='http',
        upstream=[],
        checker_name='anonymous',
        verify_urls_from_redis=from_redis,
        verify_urls=['http://httpbin.org/ip'],
        enable=True,
        interval=1
    )
    settings_dict.update({'SCENE_TASKS': [scene_task.dict()]})
    crawler = crawler_factory(settings_dict)
    spider = SceneSpider.from_crawler(crawler, 'http')
    url = spider.random_verification_url()
    assert url == expect_value


@pytest_twisted.inlineCallbacks
@pytest.mark.parametrize(
    'keywords, score',
    [
        (['example'], 1),
        (['foo'], -1)
    ]
)
def test_parse(mocker, settings_dict, keywords, score):
    """Test parse"""
    mocker.patch.object(
        Redis,
        'execute_command',
        return_value='127.0.0.1:1080'
    )
    mocker.patch.object(
        SceneSpider,
        'make_request_from_url',
        return_value=Request('http://example.com')
    )
    mocker.patch.object(SceneSpider, 'spider_idle', return_value=None)
    settings_dict.update({
        'ITEM_PIPELINES': [],
        'REDIS_START_URL_BATCH_SIZE': 1,
        'GFW_PROXY': None,
        'SCENE_TASKS': [
            {
                'name': 'foo',
                'upstream': [],
                'checker_name': 'keywords',
                'verify_urls': ['http://example.com'],
                'checker_rule': {'keywords': keywords, },
                'enable': True,
                'interval': 1
            }
        ]
    })
    runner = CrawlerRunner(settings_dict)
    runner_crawler = runner.create_crawler(SceneSpider)
    items = []

    def _(item):
        items.append(item)

    runner_crawler.signals.connect(_, signal=signals.item_scraped)
    yield runner_crawler.crawl('foo')
    assert items[0]['score'] == score


def test_parse_exception(mocker, crawler):
    """Test parse exception"""
    spider = SceneSpider.from_crawler(crawler, 'foo')

    mocker.patch.object(spider.checker, 'check', side_effect=Exception('foo'))
    res = list(spider.parse(mocker.MagicMock()))
    assert len(res) == 1
    assert not res[0]


@pytest_twisted.inlineCallbacks
def test_parse_error(mocker, settings_dict):
    """test parse error"""
    mocker.patch.object(
        Redis,
        'execute_command',
    )
    # mock request.meta.proxy
    # Because of Request.meta be Property decorated,
    # we mock it to PropertyMock, and return {}, avoid
    # request.meta.proxy to be used.
    mocker.patch.object(
        Request,
        'meta',
        new_callable=mocker.PropertyMock,
        return_value={}
    )

    # mock to call parse_error.
    # Only response is ok, and SpiderMiddleware.process_spider_input
    # raise Exception, Request.errback can be called.
    # So we mock it and add this middleware to settings.
    class RaiseExceptionSpiderMiddleware:  # pylint: disable=too-few-public-methods
        """Raise exception in spider middleware"""

        def process_spider_input(self, response, spider):  # pylint: disable=no-self-use
            """Raise exception"""
            raise Exception('foo')

    mws = settings_dict.get('SPIDER_MIDDLEWARES')
    mws.setdefault(RaiseExceptionSpiderMiddleware, 700)

    settings_dict.update({
        'SPIDER_MIDDLEWARES': mws,
        'ITEM_PIPELINES': [],
        'REDIS_START_URL_BATCH_SIZE': 1,
        'GFW_PROXY': None,
        'SCENE_TASKS': [
            {
                'name': 'foo',
                'upstream': [],
                'interval': 1,
                'enable': True,
                'verify_urls': ['http://example.com'],
                'checker_name': 'keywords',
                'checker_rule': {'keywords': ['foo']}
            }
        ]
    })
    settings_dict.update({})
    mocker.patch.object(SceneSpider, 'spider_idle', return_value=None)
    runner_crawler = CrawlerRunner(settings_dict).create_crawler(SceneSpider)
    # Catch scraped item
    items = []

    def _(item):
        items.append(item)

    runner_crawler.signals.connect(_, signal=signals.item_scraped)
    yield runner_crawler.crawl('foo')
    assert items[0]['score'] == -1
