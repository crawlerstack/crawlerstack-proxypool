"""Test extractor"""
import logging

import pytest
from crawlerstack_proxypool.common.extractor import (HtmlExtractor,
                                                     JsonExtractor,
                                                     proxy_check)
from httpx import Response

logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    'ip_address, port',
    [
        ('127.0.0.1', 8080),
        ('127.0.0.1', '8080'),

    ]
)
def test_proxy_check(ip_address, port):
    """Test proxy check"""
    assert proxy_check(ip_address, port)
    assert not proxy_check('127.0.0.1', 808080)


# @pytest.mark.asyncio
# async def test_parse(mocker):
#     """Test parse"""
#     base_extractor = BaseExtractor(mocker.MagicMock())
#     with pytest.raises(NotImplementedError):
#         await base_extractor.parse()


@pytest.mark.parametrize(
    'tag, ip, port,columns_rule,row_end',
    [
        (None, None, None, False, None),
        ('<td>透明</td>', '<td>127.0.0.11</td>', '<td>8080</td>', 'td', 2),
        ('<td>透明</td>', '<td>127.0.0.11</td>', '<td>8080</td>', 'td', None),
        ('<td>transparent</td>', '<td>127.0.0.11</td>', '<td>8080</td>', 'td', None),
    ]
)
@pytest.mark.asyncio
async def test_html_parse(mocker, tag, ip, port, columns_rule, row_end):
    """Test Html Extractor """

    html_parse = HtmlExtractor.from_kwargs(
        mocker.MagicMock(),
        rows_rule='//tr',
        row_start=1,
        row_end=row_end,
        columns_rule=columns_rule,
        ip_position=0,
        port_position=1,
        ip_rule='text()',
        port_rule='text()'

    )
    text = f'''
<html>
<head>
    <title>test ip</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
</head>
<body>
<div id="main" class="container">
    <div class="containerbox boxindex">
        <table width='100%' border="2px" cellspacing="0px" bordercolor="#6699ff">
            <tr>
                <td>ip</td>
                <td>端口号</td>
                <td>代理位置</td>
                <td>代理类型</td>
                <td>验证时间</td>
            </tr>
            <tr>
                {tag}
            </tr>
            <tr>
                {ip}
                {port}
            </tr>
        </table>
    </div>
</div>
</div>
</body>
</html>
    '''
    response = mocker.MagicMock(text=text, return_value=Response)

    if ip is not None:
        result_items = await html_parse.parse(response)
        assert result_items == ['http://127.0.0.11:8080', 'https://127.0.0.11:8080']
    if ip is None:
        result_items = await html_parse.parse(response)
        assert result_items == []
    if ip is None and port is None:
        result_items = await html_parse.parse(response)
        assert result_items == []


@pytest.mark.parametrize(
    'test_text',
    [
        '[{"port": 80 ,"ip": "162.214.202.170"}]',
        '[{"ip":"127.0.0.1"}]',
        '[{"port": 808080 ,"ip": "162.214.202.170"}]'
    ]
)
@pytest.mark.asyncio
async def test_json_parse(mocker, test_text, caplog):
    """Test Json Extractor"""
    test_text = test_text
    response = mocker.MagicMock(text=test_text, return_value=Response)
    json_parse = JsonExtractor.from_kwargs(
        mocker.MagicMock(),
        ip_key='ip',
        port_key='port'
    )
    if test_text == '[{"ip":"127.0.0.1"}]':
        caplog.set_level(logging.WARNING)
        result = await json_parse.parse(response)
        assert result == []
        assert 'Parse info error' in caplog.text
    if test_text == '[{"port": 808080 ,"ip": "162.214.202.170"}]':
        result = await json_parse.parse(response)
        assert result == []
    if test_text == '[{"port": 80 ,"ip": "162.214.202.170"}]':
        result = await json_parse.parse(response)
        assert result == ['http://162.214.202.170:80', 'https://162.214.202.170:80']
