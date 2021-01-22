"""Test pipeline"""
import logging

import pytest
import pytest_twisted
from redis import Redis
from scrapy.crawler import CrawlerRunner

from crawlerstack_proxypool.core.base import BaseParserSpider
from crawlerstack_proxypool.core.items import ProxyUrlItem, SceneItem
from crawlerstack_proxypool.dao.scene import SceneRedisDao


@pytest.fixture(name='runner_crawler')
def fixture_runner_crawler(mocker, settings_dict):
    """Runner crawler fixture"""
    mocker.patch.object(Redis, 'execute_command', return_value='http://example.com')
    mocker.patch.object(BaseParserSpider, 'spider_idle', return_value=None)
    settings_dict.update({
        'REDIS_START_URL_BATCH_SIZE': 1,
        'GFW_PROXY': None,
        # 'SCENE_TASKS': [
        #     {
        #         'name': 'foo',
        #         'upstream': [],
        #         'interval': 1,
        #         'enable': True,
        #         'verify_urls': ['http://httpbin.org/ip'],
        #         'checker_name': 'keywords'
        #     }
        # ]
    })
    runner = CrawlerRunner(settings_dict)
    yield runner.create_crawler(BaseParserSpider)


@pytest_twisted.inlineCallbacks
def test_raw_ip_pipeline(mocker, runner_crawler, caplog):
    """Test raw ip pipeline"""
    mocker.patch.object(
        BaseParserSpider,
        'parse',
        return_value=[ProxyUrlItem(url='127.0.0.1:1080')]
    )
    mock_sadd = mocker.patch.object(Redis, 'sadd')
    with caplog.at_level(level=logging.DEBUG):
        yield runner_crawler.crawl('foo')
        mock_sadd.assert_any_call('crawlerstack_proxypool:foo:seed', '127.0.0.1:1080')


@pytest_twisted.inlineCallbacks
def test_scene_pipeline(mocker, runner_crawler, caplog):
    """Test scene pipeline"""
    item = SceneItem(
        url='http://example.com',
        scene='http',
        speed=1,
        time=1,
        score=1,
    )
    mocker.patch.object(
        BaseParserSpider,
        'parse',
        return_value=[item, {'a': 1}]
    )
    mock_update = mocker.patch.object(SceneRedisDao, 'update')
    with caplog.at_level(level=logging.DEBUG):
        yield runner_crawler.crawl('foo')
        mock_update.assert_called_once_with(
            item['url'],
            item['score'],
            item['speed'], item['time']
        )
