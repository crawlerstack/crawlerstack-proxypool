"""Test parsers"""

from typing import Dict, List, Union

import pytest
from scrapy.http import Response

from crawlerstack_proxypool.core.parsers import (BaseParser, HtmlParser,
                                                 JsonParser, TextParser)
from tests.conftest import (ExpectValueType, RuleType, TextType,
                            proxy_div_html, proxy_table_html)


def _test_parse(
        parser: BaseParser,
        response: Response,
        rule: Dict[str, str],
        expect_value: List[str]
):
    data = parser.parse(response=response, **rule)
    assert data == expect_value


TestDataType = List[Dict[str, Union[TextType, RuleType, ExpectValueType]]]


class BaseTestParse:
    """Base test"""
    parser_kls: None
    parser_data: TestDataType
    parser_error_data: TestDataType

    @pytest.fixture()
    def parser(self, mocker):
        """parser fixture"""
        return self.parser_kls(mocker.MagicMock())

    def test_parses(self, parser, response_factory):
        """Test parse"""
        for data in self.parser_data:
            _test_parse(
                parser,
                response_factory(data.get('text')),
                data.get('rule', {}),
                data.get('expect_value')
            )

    def test_parse_error(self, mocker, parser, response_factory):
        """Test parse error"""
        for data in self.parser_error_data:
            mocker.patch(
                'crawlerstack_proxypool.core.parsers.proxy_check',
                side_effect=ValueError('foo')
            )
            _test_parse(
                parser,
                response_factory(data.get('text')),
                data.get('rule', {}),
                data.get('expect_value', [])
            )
            parser.spider.logger.warning.assert_called_once()


class TestTextParser(BaseTestParse):
    """Test test parser"""
    parser_kls = TextParser
    parser_data = [
        {
            'text': 'http://127.0.0.1:5000\r\n'
                    'http://127.0.0.1:0\r\n'
                    'http://127.0.0.1\r\n'
                    'http://127.0.0.1:',
            'rule': {'redundancy': 'http://'},
            'expect_value': ['127.0.0.1:5000'],
        },
        {
            'text': '<div>'
                    'http://127.0.0.1:5000\r\n'
                    'http://127.0.0.1:0\r\n'
                    'http://127.0.0.1\r\n'
                    'http://127.0.0.1:'
                    '</div>',
            'rule': {'redundancy': 'http://', 'pre_extract': '//div/text()'},
            'expect_value': ['127.0.0.1:5000'],
        }
    ]
    parser_error_data: TestDataType = [
        {
            'text': 'http://127.0.0.1:5000',
        }
    ]


class TestJsonParser(BaseTestParse):
    """Test json parser"""
    parser_kls = JsonParser
    parser_data = [
        {
            'text': [
                {'ip': '127.0.0.1', 'port': 1080},
                {'ip': '127.0.0.1', 'port': 0}
            ],
            'expect_value': ['127.0.0.1:1080']
        }
    ]
    parser_error_data = [
        {
            'text': [
                {'ip': '127.0.0.1', 'port': 1080},
            ],
        }
    ]


class TestHtmlParser(BaseTestParse):
    """Test html parser"""
    parser_kls = HtmlParser
    parser_data = [
        {
            'text': proxy_table_html,
            'expect_value': ['127.0.0.1:1080']
        },
        {
            'text': proxy_div_html,
            'rule': {
                'row_start': 0,
                'row_end': -1,
                'rows_rule': '//div/text()',
                'columns_rule': None
            },
            'expect_value': ['127.0.0.1:1080']
        }
    ]
    parser_error_data = [
        {
            'text': proxy_table_html,
        },
    ]
