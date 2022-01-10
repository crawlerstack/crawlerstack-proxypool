import pytest

from crawlerstack_proxypool.crawler.parser import DefaultParser


@pytest.mark.asyncio
async def test_default_parse(mocker):
    parser = DefaultParser(mocker.MagicMock())
    resp_mock = mocker.MagicMock()
    resp_mock.text = 'foo'
    result = await parser.parse(resp_mock)
    assert result.get('text') == 'foo'
