"""Test checker"""
from typing import List

import pytest
import pytest_twisted
from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler
from scrapy.http import HtmlResponse

from crawlerstack_proxypool.core.checkers import (AnonymousChecker,
                                                  KeyWordsChecker)


@pytest_twisted.inlineCallbacks
@pytest.mark.parametrize(
    'public_ip, checked_ip',
    [
        ('127.0.0.1', '127.0.0.1'),
        ('127.0.0.1', '127.0.0.2'),
        ('', '127.0.0.2'),
    ]
)
def test_anonymous_checker(mocker, spider, public_ip, checked_ip):
    """Test anonymous checker"""
    mocker.patch.object(
        HTTP11DownloadHandler,
        'download_request',
        return_value=HtmlResponse(
            'http://example.com',
            body=f'{{"origin": "{public_ip}"}}'.encode()
        )
    )
    checker = AnonymousChecker(spider)
    resp = HtmlResponse(
        'http://example.com',
        body=f'{{"origin": "{checked_ip}"}}'.encode()
    )
    if public_ip:
        assert checker.origin
        assert checker.check(response=resp) != (public_ip == checked_ip)

    if not public_ip:
        with pytest.raises(Exception, match='Local public IP is invalid.'):
            checker.check(response=resp)
    yield checker._spider_closed()  # pylint: disable=protected-access


@pytest.mark.parametrize(
    'resp_txt, keywords, strict, expect_value',
    [
        ('<div>abc</div><b>ddd</b>', ['abc', 'ddd'], False, True),
        ('<div>abc</div><b>ddd</b>', ['abc', 'ddd'], True, True),
        ('<div>abc</div><b>ddd</b>', ['foo', 'ddd'], False, True),
        ('<div>abc</div><b>ddd</b>', ['foo', 'ddd'], True, False),
        ('<div>abc</div><b>ddd</b>', ['foo'], False, False),
        ('<div>abc</div><b>ddd</b>', ['foo'], True, False),
        ('<div>abc</div><b>ddd</b>', ['ddd'], False, True),
        ('<div>abc</div><b>ddd</b>', ['ddd'], True, True),
    ]
)
def test_keywords_checker(
        spider,
        resp_txt: str,
        keywords: List,
        strict,
        expect_value
):
    """Test keywords checker"""
    checker = KeyWordsChecker(spider)
    resp = HtmlResponse('http://example.com', body=resp_txt.encode())
    rest = checker.check(response=resp, keywords=keywords, strict=strict)
    assert expect_value == rest
