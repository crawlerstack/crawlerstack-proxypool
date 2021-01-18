"""Test config"""
import json
import textwrap
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

import pytest
from scrapy import Spider
from scrapy.http import HtmlResponse, Response
from scrapy.utils.test import get_crawler as scrapy_get_crawler

from crawlerstack_proxypool.config import settings

JsonDataType = List[Dict[str, Union[int, str]]]
TextType = Union[Path, str, JsonDataType, Dict[str, JsonDataType]]
RuleType = Dict[str, str]
ExpectValueType = List[str]


@pytest.fixture()
def settings_dict() -> Dict:
    _s = settings.as_dict()
    spider_tasks = [
        {
            'parser_rule': {
            },
            'name': 'foo',
            'task_type': 'general',
            'parser_name': 'html',
            'interval': 1,
            'enable': True,
            'resource': []
        }
    ]
    _s.update({'SPIDER_TASKS': spider_tasks})
    return _s


@pytest.fixture()
def get_crawler_factory():
    """get crawler factory"""

    def _(settings_dict=None, spider_kls=None):
        return scrapy_get_crawler(spider_kls, settings_dict=settings_dict or settings.as_dict())

    return _


@pytest.fixture()
def crawler(get_crawler_factory):
    yield get_crawler_factory()


@pytest.fixture()
def get_spider_factory(crawler):
    def _(spider_kls: Type[Spider], *args, **kwargs):
        return spider_kls.from_crawler(crawler, *args, **kwargs)

    return _


@pytest.fixture()
def spider(get_spider_factory):
    """spider fixture"""
    yield get_spider_factory(Spider, 'foo')


test_data_dir = Path(__file__).parent / 'data'


@pytest.fixture()
def response_factory():
    """Response factory fixture"""

    def _(
            text: TextType,
            response_kls: Optional[Type[Response]] = HtmlResponse
    ) -> Response:

        if isinstance(text, str):
            body = text.encode('utf-8')
        elif isinstance(text, Path):
            with open(str(text), 'rb') as file:
                body = file.read()
        else:
            body = json.dumps(text).encode('utf-8')
        return response_kls(
            url='http://example.com',
            body=body
        )

    return _


proxy_table_html = textwrap.dedent("""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>proxy</title>
        <style>
            #ip_list, table tr th, table tr td {
                border: 2px solid;
            }
    
            table td {
                text-align: center;
            }
    
            table {
                border-collapse: collapse
            }
    
        </style>
    </head>
    <body>
    <table id="ip_list">
        <tr>
            <th>IP</th>
            <th>PORT</th>
            <th>Anonymity</th>
        </tr>
        <tr>
            <td>127.0.0.1</td>
            <td>1080</td>
            <td>Anonymous</td>
        </tr>
        <tr>
            <td>127.0.0.1</td>
            <td>0</td>
            <td>transparent</td>
        </tr>
    </table>
    </body>
    </html>
    """)

proxy_div_html = textwrap.dedent("""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>proxy</title>
    </head>
    <body>
    <div>127.0.0.1:1080</div>
    <div>127.0.0.1:0</div>
    <div>foo</div>
    </body>
    </html>
    """)
