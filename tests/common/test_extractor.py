import pytest
from httpx import Response
from lxml import etree, html

from crawlerstack_proxypool.common.extractor import proxy_check, HtmlExtractor, HtmlExtractorParams


@pytest.mark.parametrize(
    'ip, port, value',
    [
        ('127.0.0.1', 22, True),
        ('127.0.0.1', 10086, True),
        ('127.0.0.1', 888888, False),
        ('127.0.0.888', 22, False),
    ]
)
def test_proxy_check(ip, port, value):
    res = proxy_check(ip, port)
    assert res == value


class TestHtmlExtractor:

    @pytest.fixture()
    def extractor(self, mocker):
        obj = HtmlExtractor.from_params(mocker.MagicMock())
        return obj

    @pytest.mark.parametrize(
        'attr,text, value',
        [
            # ({}, '<tr><td>127.0.0.1</td><td>8080</td>', 2),
            ({'columns_rule': None}, '127.0.0.1:1080', 2),
        ]
    )
    @pytest.mark.asyncio
    def test_parse_row(self, mocker, extractor, attr, text, value):
        for k, v in attr.items():
            mocker.patch.object(extractor.params, k, v)
        ele = html.fragment_fromstring(text)
        res = extractor.parse_row(ele)
        if res is not None:
            assert len(res) == value
        else:
            assert res == value

    @pytest.mark.parametrize(
        'text, value',
        [
            (('<tr><td>ip</td></tr><tr><td>port</td></tr>'
              '<tr><td>127.0.0.1</td></tr><tr><td>8080</td></tr>'), 0)
        ]
    )
    @pytest.mark.asyncio
    async def test_parse(self, mocker, extractor, text, value):
        resp_mocker = mocker.patch.object(Response, 'text', new_callable=mocker.PropertyMock, return_value=text)
        res = await extractor.parse(Response(status_code=200))
        print(len(res))
