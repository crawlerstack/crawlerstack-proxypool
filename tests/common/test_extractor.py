import pytest
from httpx import Response
from lxml import etree, html

from crawlerstack_proxypool.common.extractor import (HtmlExtractor,
                                                     HtmlExtractorParams,
                                                     JsonExtractor,
                                                     proxy_check)


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
        'attr, text, value',
        [
            ({}, '<tr><td>127.0.0.1</td><td>8080</td></tr>', 2),
            ({'port_position': None}, '<tr><td>127.0.0.1:1080</td></tr>', 2),
            ({}, '<tr><td>127.0.0.1</td></tr>', None),
        ]
    )
    @pytest.mark.asyncio
    def test_parse_row(self, mocker, extractor, attr, text, value):
        for k, v in attr.items():
            mocker.patch.object(extractor.params, k, v)
        ele = html.fragment_fromstring(text)
        res = extractor.parse_row(ele.xpath(extractor.params.rows_rule)[0])
        if res is not None:
            assert len(res) == value
        else:
            assert res == value

    @pytest.mark.parametrize(
        'attr, text, value',
        [
            (
                    {'row_end': None},
                    ('<tr><td>ip</td><td>port</td></tr>'
                     '<tr><td>127.0.0.1</td><td>8080</td></tr>'),
                    1,
            ),
            (
                    {'row_end': None},
                    ('<tr><td>ip</td><td>port</td><td>Anonymity</td></tr>'
                     '<tr><td>127.0.0.1</td><td>8080</td><td>transparent</td></tr>'),
                    0,
            ),
        ]
    )
    @pytest.mark.asyncio
    async def test_parse(self, mocker, extractor, attr, text, value):
        for k, v in attr.items():
            mocker.patch.object(extractor.params, k, v)
        mocker.patch.object(Response, 'text', new_callable=mocker.PropertyMock, return_value=text)
        mocker.patch.object(extractor, 'parse_row', return_value=[1])
        res = await extractor.parse(Response(status_code=200))
        assert len(res) == value


@pytest.mark.parametrize(
    'text, value',
    [
        ('[{"ip": "127.0.0.1", "port": 22}]', 2),
        ('[{"ip": "127.0.0.1", "port": 88888}]', 0),
    ]
)
@pytest.mark.asyncio
async def test_json_extractor(mocker, text, value):
    extractor = JsonExtractor.from_params(mocker.MagicMock())
    mocker.patch.object(Response, 'text', new_callable=mocker.PropertyMock, return_value=text)
    res = await extractor.parse(Response(status_code=200))
    assert len(res) == value
