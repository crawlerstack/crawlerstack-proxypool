"""Test checker"""
import asyncio

import pytest
from httpx import URL, Response

from crawlerstack_proxypool.common.checker import (AnonymousChecker,
                                                   CheckedProxy,
                                                   KeywordChecker)


@pytest.mark.parametrize(
    'url, alive',
    [
        (URL('http://localhost'), True),
        (URL('http://localhost'), False)
    ]
)
def test_checked_proxy(url, alive):
    """Test checked proxy"""
    if alive:
        checked_proxy = CheckedProxy(url=url, alive=alive)
        assert checked_proxy.alive_status == 1
    if not alive:
        checked_proxy = CheckedProxy(url=url, alive=alive)
        assert checked_proxy.alive_status == -1


@pytest.mark.asyncio
async def test_check(mocker):
    """Test keyword check"""
    response = mocker.MagicMock(status_code=200, return_value=Response, text='test')
    keyword_check = KeywordChecker.from_kwargs(
        mocker.MagicMock()
    )
    result = await keyword_check.check(response=response)
    assert result.alive
    assert result.alive_status == 1


@pytest.mark.parametrize(
    'keywords, check_any',
    [
        (['t'], False),
        (['A'], False),
        (['t'], True),
        (['A'], True)
    ]
)
def test_check_keywords(mocker, keywords, check_any):
    """Test KeywordChecker.check_keywords"""
    text = 'test'
    check_keywords = KeywordChecker.from_kwargs(
        mocker.MagicMock(),
        keywords=keywords,
        any=check_any
    )
    for k in keywords:
        if k in text:
            assert check_keywords.check_keywords(text)
        else:
            assert not check_keywords.check_keywords(text)


@pytest.mark.asyncio
async def test_open_spider(mocker):
    """Test BaseChecker parse"""
    refresh_public_ip = mocker.patch.object(AnonymousChecker, 'refresh_public_ip')
    await AnonymousChecker(mocker.MagicMock()).open_spider()

    refresh_public_ip.assert_called_with()


@pytest.mark.asyncio
async def test_refresh_public_ip(mocker):
    """Test refresh public ip"""
    anonymous_checker = AnonymousChecker(mocker.MagicMock())
    get_public_ip = mocker.patch.object(AnonymousChecker, 'get_public_ip')

    async def close():
        await asyncio.sleep(0.01)
        await anonymous_checker.close_spider()

    close_task = asyncio.create_task(close())
    await anonymous_checker.open_spider()
    await close_task

    get_public_ip.assert_called_with()


@pytest.mark.asyncio
async def test_get_public_ip(mocker):
    """Test get public ip"""
    anonymous_checker = AnonymousChecker(mocker.MagicMock())
    await anonymous_checker.get_public_ip()

    assert anonymous_checker._public_ip is not None


@pytest.mark.parametrize(
    'strict, text, public_ip',
    [
        (False, 'foo', 'foo'),
        (False, '', 'foo'),
        (False, 'foo', ''),
        (False, '', ''),
        (True, 'foo', 'foo'),
    ]
)
@pytest.mark.asyncio()
async def test_anonymous_checker_check(mocker, strict, text, public_ip):
    """Test AnonymousChecker check"""
    response = mocker.MagicMock(text=text, status_code=200, proxy='test')
    anonymous = AnonymousChecker.from_kwargs(
        mocker.MagicMock(),
        strict=strict,
    )
    mocker.patch.object(anonymous, '_public_ip', public_ip)
    assert await anonymous.check(response)
