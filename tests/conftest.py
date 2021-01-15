"""Test config"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Type, Union

import pytest
from scrapy.http import HtmlResponse, Response
from scrapy.utils.test import get_crawler as scrapy_get_crawler

from crawlerstack_proxypool.config import settings

JsonDataType = List[Dict[str, Union[int, str]]]
TextType = Union[Path, str, JsonDataType, Dict[str, JsonDataType]]
RuleType = Dict[str, str]
ExpectValueType = List[str]


@pytest.fixture()
def get_crawler():
    """get crawler factory"""

    def _(**kwargs):
        return scrapy_get_crawler(settings_dict=kwargs or settings.as_dict())

    return _


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
