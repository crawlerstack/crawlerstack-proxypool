"""Test middleware"""
import random
import time

import pytest
from scrapy import Request, Spider
from scrapy.exceptions import NotConfigured
from scrapy_splash import SplashRequest

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core.middlewares import (ProxyMiddleware,
                                                     RequestProfileMiddleware,
                                                     UserAgentMiddleware)


def test_user_agent_middleware(spider):
    """Test user-agent mw"""
    request = Request('http://example.com')
    middleware = UserAgentMiddleware()
    assert 'User-Agent' not in request.headers
    middleware.process_request(request, spider)
    assert 'User-Agent' in request.headers


class TestProxyMiddleware:
    """Test ProxyMiddleware"""
    mw_kls = ProxyMiddleware

    @pytest.fixture(name='middleware')
    def fixture_proxy_mw(self, crawler):
        """mw fixture"""
        yield self.mw_kls.from_crawler(crawler)

    def test_from_crawler(self, crawler_factory):
        """Test from_crawler"""
        with pytest.raises(NotConfigured, match='GFW_PROXY'):
            self.mw_kls.from_crawler(crawler_factory({'A': 1}))

    def test_process_request_scene(self, spider, middleware):  # pylint: disable=no-self-use
        """Test process_request with scene"""
        request = Request('http://example.com', meta={'scene': True})
        middleware.process_request(request, spider)
        assert 'proxy' not in request.meta

    @pytest.mark.parametrize('is_splash', [True, False])
    def test_process_request_gfw(self, crawler, middleware, is_splash):  # pylint: disable=no-self-use
        """Test gfw"""
        spider = Spider.from_crawler(crawler, 'foo', gfw=True)
        if is_splash:
            request = SplashRequest('http://example.com')
        else:
            request = Request('http://example.com')
        middleware.process_request(request, spider)
        if is_splash:
            proxy = request.meta['splash']['args']['proxy']
        else:
            proxy = request.meta['proxy']
        assert proxy == settings.GFW_PROXY

    @pytest.mark.parametrize(
        'mock_value, has_proxy',
        [
            (0, False),
            (1, True)
        ]
    )
    def test_process_request_not_gfw(
            self,
            mocker,
            spider,
            middleware,
            mock_value,
            has_proxy
    ):  # pylint: disable=no-self-use, disable=too-many-arguments
        """Test no gfw"""
        mocker.patch.object(random, 'randint', return_value=mock_value)
        request = Request('http://example.com')
        middleware.process_request(request, spider)
        if has_proxy:
            assert 'proxy' in request.meta
        else:
            assert 'proxy' not in request.meta


def test_request_profile_middleware(mocker):
    """Test RequestProfileMiddleware"""
    spider = mocker.MagicMock()
    request = Request('http://example.com')
    middleware = RequestProfileMiddleware()
    start = time.perf_counter()
    middleware.process_request(request, spider)
    middleware.process_exception(request, Exception(), spider)
    ex_interval = int((time.perf_counter() - start) * 1000)
    assert 'start' in request.meta
    assert 'speed' in request.meta
    assert 0 <= request.meta['speed'] <= ex_interval

    middleware.process_response(request, mocker.MagicMock(), spider)
    done_interval = int((time.perf_counter() - start) * 1000)

    assert ex_interval <= request.meta['speed'] <= done_interval
