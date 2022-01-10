import pytest

from crawlerstack_proxypool.common import AnonymousChecker, ParserFactory
from crawlerstack_proxypool.task import ValidateSpiderTask


class TestValidateSpiderTask:
    @pytest.fixture()
    def task(self):
        task = ValidateSpiderTask(
            'http',
            'http',
            ['http://httpbin.iclouds.work/ip'],
            parser_kls=ParserFactory('anonymous').get_checker(),
            sources=['http'],
        )
        yield task

    @pytest.mark.asyncio
    async def test_start(self, task, init_proxy_status):
        # TODO 修复 spider 逻辑中，由于 spider.stop ，导致 pipeline_handler 等操作失效
        # 问题出在 asyncio.gather(*self._active_downloader) 完成后，
        # 执行了 Spider.close ，导致后续操作无效
        await task.start()
