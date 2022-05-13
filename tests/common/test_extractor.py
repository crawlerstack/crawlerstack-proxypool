"""Test extractor"""
import pytest
from crawlerstack_proxypool.common.extractor import JsonExtractor, HtmlExtractor, \
    HtmlExtractorKwargs, BaseExtractor
from crawlerstack_proxypool.common.extractor import proxy_check
import httpx


@pytest.fixture()
def baseextractor():
    """BaseExtractor fixture"""
    yield BaseExtractor()


@pytest.fixture()
def htmlextractorkwargs():
    """HtmlExtractorKwargs fixture"""
    yield HtmlExtractorKwargs()


@pytest.fixture()
def htmlextractor():
    """HtmlExtractor fixture"""
    yield HtmlExtractor()


@pytest.fixture()
def jsonextractor():
    """JsonExtractor fixture"""
    yield JsonExtractor()


@pytest.fixture()
def test_proxy_check():
    """Test proxy_check"""

    efficient = proxy_check('45.184.155.9', 999)
    assert str(efficient) == 'True'


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
"""Test extractor"""
import pytest
from crawlerstack_proxypool.common.extractor import JsonExtractor, HtmlExtractor, \
    HtmlExtractorKwargs, BaseExtractor
from crawlerstack_proxypool.common.extractor import proxy_check
import httpx


@pytest.fixture()
def baseextractor():
    """BaseExtractor fixture"""
    yield BaseExtractor()


@pytest.fixture()
def htmlextractorkwargs():
    """HtmlExtractorKwargs fixture"""
    yield HtmlExtractorKwargs()


@pytest.fixture()
def htmlextractor():
    """HtmlExtractor fixture"""
    yield HtmlExtractor()


@pytest.fixture()
def jsonextractor():
    """JsonExtractor fixture"""
    yield JsonExtractor()


@pytest.fixture()
def test_proxy_check():
    """Test proxy_check"""

    efficient = proxy_check('45.184.155.9', 999)
    assert str(efficient) == 'True'


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
