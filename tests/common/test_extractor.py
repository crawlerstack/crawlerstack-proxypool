"""Test extractor"""
import pytest
from httpx import Response
import typing
from crawlerstack_proxypool.common.extractor import BaseExtractor, JsonExtractor, HtmlExtractor, HtmlExtractorKwargs, \
    BaseExtractor
from crawlerstack_proxypool.common.extractor import proxy_check
from crawlerstack_proxypool.aio_scrapy.spider import Spider
import httpx


class Foo(Spider):
    """Foo spider"""

    async def parse(self, response: Response) -> typing.Any:
        pass


@pytest.fixture()
def foo_spider():
    yield Foo(name='test', start_urls=['http://www.66ip.cn/'])


@pytest.fixture()
def baseextractor():
    """BaseExtractor fixture"""
    baseextractor = BaseExtractor(foo_spider())
    yield baseextractor


@pytest.fixture()
def htmlextractorkwargs():
    """HtmlExtractorKwargs fixture"""
    yield HtmlExtractorKwargs()


@pytest.fixture()
def htmlextractor():
    """HtmlExtractor fixture"""
    htmlextractor = HtmlExtractor(baseextractor())
    yield htmlextractor


@pytest.fixture()
def jsonextractor():
    """JsonExtractor fixture"""
    yield JsonExtractor()


@pytest.fixture()
def test_proxy_check():
    """Test proxy_check"""

    efficient = proxy_check('45.184.155.9', 999)
    assert efficient == True


@pytest.fixture()
def test_from_kwargs():
    BaseExtractor.from_kwargs()


@pytest.mark.parametrize(
    'rows_rule,row_start,row_end,columns_rule,ip_position,port_position,ip_rule,port_rule',
    [
        ('//tr', 1, None, 'td', 0, 1, 'text()', 'text()'),
    ]
)
async def test_html_extractor_parse(rows_rule, row_start, row_end):
    htmlextractorkwargs.rows_rule = rows_rule
    htmlextractorkwargs.row_start = row_start
    htmlextractorkwargs.row_end = row_end
    items = await htmlextractor.parse()
    assert items != None


@pytest.fixture()
def test_parse():
    """Test parse"""
    response = httpx.get('http://www.66ip.cn/')
    htmlextractor.parse(response)


@pytest.fixture()
async def test_jsonextractor(baseextractor):
    response = httpx.get('https://cool-proxy.net/proxies.json')
    result_list = jsonextractor.parse(response)
    assert result_list == ['http://162.214.202.170:80', 'https://162.214.202.170:80', 'http://66.29.154.103:3128',
                           'https://66.29.154.103:3128', 'http://66.29.154.105:3128', 'https://66.29.154.105:3128']
