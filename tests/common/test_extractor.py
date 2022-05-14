"""Test extractor"""
import pytest
from bs4 import BeautifulSoup
from httpx import Response
import typing
from crawlerstack_proxypool.common.extractor import JsonExtractor, HtmlExtractor, HtmlExtractorKwargs, \
    BaseExtractor
from crawlerstack_proxypool.common.extractor import proxy_check
from crawlerstack_proxypool.aio_scrapy.spider import Spider
import httpx


class Foo(Spider):
    """Foo spider"""

    async def parse(self, response: Response) -> typing.Any:
        pass


@pytest.fixture(name='mock_json')
def fixture_mock_json(requests_mock):
    """fixture mock json"""
    requests_mock.get('http://test_json.com',
                      text='"[{"port": 80, "score": 150.549, "update_time": 1652509227.0, "anonymous": 1, "download_speed_average": 56917.2, "response_time_average": 6.10687, "country_code": "US", "ip": "162.214.202.170", "working_average": 87.8431, "country_name": "United States"}]"')
    response = httpx.get('http://test_json.com')
    yield response


@pytest.fixture(name='mock_html')
def fixture_mock_html(requests_mock):
    """fixture mock html"""
    soup = BeautifulSoup(open('ss.html', encoding='utf-8'), features='html.parser')
    requests_mock.get('http://test_html.com',
                      text=soup)
    response = httpx.get('http://test_html.com')
    yield response


@pytest.fixture()
def baseextractor():
    """BaseExtractor fixture"""
    baseextractor = BaseExtractor()
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
    yield JsonExtractor(baseextractor)


@pytest.fixture()
def test_proxy_check():
    """Test proxy_check"""
    return_value = proxy_check('45.184.155.9', 999)
    assert return_value


@pytest.fixture()
def test_from_kwargs():
    BaseExtractor.from_kwargs(fixture_mock_html)


@pytest.fixture()
def test_baseextractor(mocker):
    mock_baseextractor_init_kwargs = mocker.patch(
        'crawlerstack_proxypool.common.extractor.BaseExtractor.init_kwargs'
    )
    mock_baseextractor_kwargs = mocker.patch(
        'crawlerstack_proxypool.common.extractor.BaseExtractor.kwargs'
    )
    BaseExtractor.from_kwargs()
    mock_baseextractor_init_kwargs.assert_called_once_with()
    mock_baseextractor_kwargs.assert_called_once_with()


@pytest.mark.parametrize(
    'rows_rule,row_start,row_end,columns_rule,ip_position,port_position,ip_rule,port_rule',
    [
        ('//tr', 1, None, 'td', 0, 1, 'text()', 'text()'),
    ]
)
async def test_htmlextractor_parse(mocker, rows_rule, row_start, row_end):
    response = httpx.get('http://www.66ip.cn/')
    mock_htmlextractor_parse_row = mocker.patch(
        'crawlerstack_proxypool.common.HtmlExtractor.parse_row'
    )
    htmlextractorkwargs.rows_rule = rows_rule
    htmlextractorkwargs.row_start = row_start
    htmlextractorkwargs.row_end = row_end
    htmlextractor.parse(response)
    mock_htmlextractor_parse_row.assert_called_once_with()


@pytest.fixture()
def test_htmlextractor_parse():
    """Test htmlextractor parse"""
    response = fixture_mock_html()



@pytest.fixture()
async def test_jsonextractor_parse():
    response = fixture_mock_json()
    result_list = jsonextractor.parse(response)
    assert result_list == ['http://162.214.202.170:80', 'https://162.214.202.170:80']
