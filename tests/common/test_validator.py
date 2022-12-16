"""test validator"""
import asyncio

import pytest
from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.common import AnonymousValidator, KeywordValidator
from crawlerstack_proxypool.schema import ValidatedProxy
from crawlerstack_proxypool.signals import spider_closed


class TestKeywordValidator:
    """test keyword validator"""

    @pytest.fixture
    def validator(self, mocker):
        """validator"""
        _checker = KeywordValidator.from_params(mocker.MagicMock())
        yield _checker

    @pytest.mark.parametrize(
        'attr, text, expect_value',
        [
            ({'keywords': ['foo']}, 'foo, bar', True),
            ({'keywords': ['foo', 'bar']}, 'foo, bar', True),
            ({'keywords': ['foo', 'bar'], 'any': True}, 'foo, xxx', True),
            ({'keywords': ['foo', 'bar'], 'any': False}, 'foo, xxx', False),
        ]
    )
    @pytest.mark.asyncio
    async def test__check(self, mocker, validator, attr, text: str, expect_value):
        """test check"""
        for k, v in attr.items():
            mocker.patch.object(validator.params, k, v)
        mocker.patch.object(Response, 'text', new_callable=mocker.PropertyMock, return_value=text)
        mocker.patch.object(Response, 'request', new_callable=mocker.PropertyMock, return_value=mocker.MagicMock())
        checked_proxy_mocker = mocker.patch.object(ValidatedProxy, '__init__', return_value=None)
        await validator._check(Response(status_code=200))  # pylint: disable=protected-access
        assert checked_proxy_mocker.call_args.kwargs.get('alive') == expect_value


class TestAnonymousValidator:
    """test anonymous validator"""
    @pytest.fixture
    def validator(self, mocker):
        """checker fixture"""
        spider = mocker.MagicMock()
        spider.name = 'foo'
        spider.source = 'foo'
        spider.dest = ['foo']
        _checker = AnonymousValidator.from_params(spider)
        yield _checker

    @pytest.mark.asyncio
    async def test_get_public_ip(self, mocker, validator):
        """test_get_public_ip"""
        mocker.patch.object(Response, 'json', return_value={'origin': 'foo'})
        download_mock = mocker.patch.object(DownloadHandler, 'download', return_value=Response(status_code=200))
        await validator.update_internet_ip()
        download_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_public_ip_error(self, mocker, validator):
        """test_get_public_ip_error"""
        send_mocker = mocker.patch.object(spider_closed, 'send')
        mocker.patch.object(Response, 'json', return_value={'origin': 'foo'})
        mocker.patch.object(DownloadHandler, 'download', side_effect=Exception('time out'))
        with pytest.raises(Exception):
            await validator.update_internet_ip()
            await send_mocker.called_once

    @pytest.mark.asyncio
    async def test_loop_refresh_internet_ip(self, event_loop, mocker, validator):
        """test_refresh_internet_ip"""
        get_internet_ip_mocker = mocker.patch.object(validator, 'update_internet_ip')
        mocker.patch('random.randint', return_value=0.1)
        validator._running = True  # pylint: disable=protected-access
        task = event_loop.create_task(validator.refresh_internet_ip())
        await asyncio.sleep(0)
        validator._running = False  # pylint: disable=protected-access
        await asyncio.sleep(0.01)
        await task
        assert get_internet_ip_mocker.called_once

    @pytest.mark.parametrize(
        'first, internet_ip, proxy, resp, expect_value',
        [
            (True, '2.0.0.1', 'http://1.0.0.1:33', '1.0.0.1', None),
            (False, '2.0.0.1', 'http://1.0.0.1:33', '1.0.0.1', True),
            (False, '2.0.0.1', 'http://1.0.0.1:33', '2.0.0.1', False),
            (False, '2.0.0.1', 'http://1.0.0.1:33', '1.0.0.1, 2.0.0.1', False),
        ]
    )
    @pytest.mark.asyncio
    async def test__check(self, mocker, first, internet_ip, proxy, resp, validator, expect_value):
        """test check"""
        if first:
            with pytest.raises(ValueError):
                await validator._check(mocker.MagicMock())  # pylint: disable=protected-access
        else:
            mocker.patch.object(
                AnonymousValidator,
                'internet_ip',
                new_callable=mocker.PropertyMock,
                return_value=internet_ip
            )

            response = mocker.MagicMock()
            response.request.extensions = {'proxy': URL(proxy)}
            response.text = resp

            res = await validator._check(response)  # pylint: disable=protected-access
            assert res.alive == expect_value

    @pytest.mark.asyncio
    async def test_open_and_close_spider(self, mocker, validator):
        """test open and close spider"""
        refresh_mocker = mocker.patch.object(AnonymousValidator, 'update_internet_ip')
        await validator.open_spider()
        await asyncio.sleep(0)
        refresh_mocker.assert_called_once()
        await validator.close_spider()
        await asyncio.sleep(0)
        assert validator._refresh_ip_task.cancelled()  # pylint: disable=protected-access
