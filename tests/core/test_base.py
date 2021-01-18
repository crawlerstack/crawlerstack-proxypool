"""Test base"""
import logging

import pytest
from redis import Redis
from scrapy_splash import SplashRequest

from crawlerstack_proxypool.core.base import (BaseAjaxSpider, BaseParserSpider,
                                              BaseProxyIPSpider)
from crawlerstack_proxypool.core.parsers import HtmlParser
from crawlerstack_proxypool.utils.constants import QUEUE_PREFIX
from tests.conftest import proxy_table_html


class TestBaseParserSpider:
    """Test base parser spider"""
    spider_kls = BaseParserSpider

    def test_parse(self, get_crawler_factory, response_factory, settings_dict):
        """Test parse"""
        response = response_factory(proxy_table_html)
        crawler = get_crawler_factory(settings_dict=settings_dict)
        spider = self.spider_kls.from_crawler(crawler, name='foo')
        result = spider.parse(response)
        assert len(list(result)) == 2

    def test_no_task(self, get_crawler_factory, settings_dict):
        """Test no task"""
        crawler = get_crawler_factory(settings_dict)
        with pytest.raises(ValueError, match='No task config.'):
            self.spider_kls.from_crawler(crawler, name='demo')

    def test_parse_error(self, mocker, get_crawler_factory, settings_dict, caplog):
        """Test parse error"""
        spider_tasks = [
            {
                'parser_rule': {
                },
                'name': 'demo',
                'task_type': 'general',
                'parser_name': 'html',
                'interval': 1,
                'enable': True,
                'resource': []
            }
        ]
        settings_dict.update({'SPIDER_TASKS': spider_tasks})
        mocker.patch.object(HtmlParser, 'parse', side_effect=TypeError('foo'))
        crawler = get_crawler_factory(settings_dict=settings_dict)
        spider = self.spider_kls.from_crawler(crawler, name='demo')
        with caplog.at_level(logging.ERROR):
            list(spider.parse(mocker.MagicMock()))
            assert 'foo' in caplog.text


def test_base_proxy_ip_spider():
    """Test BaseProxyIpSpider"""
    spider = BaseProxyIPSpider('foo')
    assert spider.redis_key == f'{QUEUE_PREFIX}:spider:foo:seed'


def test_base_ajax_spider(mocker, get_crawler_factory, settings_dict):
    """Test BaseAjaxSpider"""
    mocker.patch.object(Redis, 'execute_command', return_value='http://example.com')
    crawler = get_crawler_factory(settings_dict)
    spider = BaseAjaxSpider.from_crawler(crawler, 'foo')
    request = next(spider.start_requests())
    assert isinstance(request, SplashRequest)
