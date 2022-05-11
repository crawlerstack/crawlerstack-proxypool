"""
Task
"""
import asyncio
import dataclasses
import functools
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Type, cast

import pytz
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from yarl import URL

from crawlerstack_proxypool.common import ParserFactory
from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.common.parser import BaseParser
from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.crawler.req_resp import RequestProxy
from crawlerstack_proxypool.service import FetchSpiderService
from crawlerstack_proxypool.spiders import FetchSpider, ValidateSpider
from crawlerstack_proxypool.db import session_provider
from crawlerstack_proxypool.signals import (start_fetch_proxy,
                                            start_validate_proxy)

logger = logging.getLogger(__name__)


class TaskManager:
    """
    任务管理。

    负责读取配置，创建爬虫任务，并加入到 apscheduler 进行调入。
    同时将对应的处理方法绑定到预定义事件上，在需要的时候，可以触发事件，
    让 apscheduler 立即调度对应的任务。
    """

    def __init__(self):
        """"""
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

        self.fetch_jobs: list[tuple[str, Job]] = []
        self.validate_fetch_jobs: list[tuple[str, Job]] = []
        self.validate_scene_jobs: list[tuple[str, Job]] = []

        start_fetch_proxy.connect(self.trigger_fetch_job)
        start_validate_proxy.connect(self.trigger_validate_job)

    def load_task(self):
        """
        从配置中加载任务。

        :return:
        """
        fetch_task_config = settings.get('fetch_task')
        validate_task_config = settings.get('validate_task')
        if fetch_task_config:
            self.load_fetch_task(fetch_task_config.to_list())
        if validate_task_config:
            self.load_validate_task(validate_task_config.to_list())

    def load_fetch_task(self, fetch_config: dict):
        """
        加载 fetch 任务。
        :param fetch_config:
        :return:
        """
        for config in fetch_config:
            name = config['name']
            parser = config['parser']
            schedule = config['schedule']
            spider = FetchSpiderTask(
                name=name,
                urls=config['urls'],
                parser_kls=ParserFactory(**parser).get_parser(),
                dest=config['dest']
            )
            task = self.scheduler.add_job(
                func=spider.start,
                name=name,
                **schedule,
            )
            self.fetch_jobs.append((name, task))

    def load_validate_task(self, validate_config: dict):
        for config in validate_config:
            name = config['name']
            sources = config['sources']
            checker = config['checker']
            schedule = config['schedule']
            spider = ValidateSpiderTask(
                name=name,
                dest=config['dest'],
                check_urls=config['urls'],
                parser_kls=ParserFactory(**checker).get_checker(),
                sources=sources,
            )
            task = self.scheduler.add_job(
                func=spider.start,
                name=name,
                **schedule,
            )
            if sources:
                self.validate_scene_jobs.append(('name', task))
            else:
                self.validate_fetch_jobs.append(('name', task))

    def trigger_fetch_job(self, **_kwargs):
        """
        触发抓取任务
        :return:
        """
        for _, job in self.fetch_jobs:
            trigger_job_run_now(job)

    def trigger_validate_job(self, sources: list[str] = None, **_kwargs):
        """
        触发校验任务。
        通过传递 source 触发不同的校验任务。
        :param sources:
        :return:
        """
        if sources:
            for _, job in self.validate_fetch_jobs:
                trigger_job_run_now(job)
        else:
            for name, job in self.validate_scene_jobs:
                if name in sources:
                    trigger_job_run_now(job)

    def start(self):
        self.scheduler.start()


def trigger_job_run_now(job: Job):
    """
    触发任务。
    :param job:
    :return:
    """
    logger.debug(f'Job "{job}" run next time: {job.next_run_time}, modifying run now.')
    job.modify(next_run_time=datetime.now())


@dataclasses.dataclass
class FetchSpiderTask:
    name: str
    urls: list[str]
    dest: list[str]
    parser_kls: Type[BaseParser] | None = None

    async def start_urls(self):
        for url in self.urls:
            yield URL(url)

    @session_provider(auto_commit=True)
    async def save(self, proxy: list[URL], session: AsyncSession):
        service = FetchSpiderService(session, self.dest)
        await service.save(proxy)

    async def start(self):
        spider = FetchSpider(
            name=self.name,
            seeds=self.start_urls(),
            parser_kls=self.parser_kls,
            pipeline_handler=functools.partial(self.save),

        )
        await spider.start()


@dataclasses.dataclass
class ValidateSpiderTask:
    name: str
    dest: str
    check_urls: list[str]
    parser_kls: Type[BaseParser] | None = None
    sources: list[str] | None = dataclasses.field(default_factory=list)

    @session_provider(auto_commit=True)
    async def start_urls(self, session: AsyncSession):
        """
        :param session:
        :return:
        """
        service = ValidateService(session)
        return await service.start_urls(self.dest, self.sources)

    @session_provider(auto_commit=True)
    async def error_handler(self, reqeust: RequestProxy, exception: Exception, session: AsyncSession):
        service = ValidateService(session)
        await service.error_handler(reqeust, exception, self.dest)

    @session_provider(auto_commit=True)
    async def save(self, proxy: CheckedProxy, session: AsyncSession):
        """
        不需要将 service = ValidateService(session) 提取出来。因为 save 任务传递到
        ValidateSpider 会放到一个 task 中运行，使用 session_provider 自动管理该 task 中的 session 生命周期。
        :param proxy:
        :param session:
        :return:
        """
        service = ValidateService(session)
        await service.save(proxy, self.dest)

    async def start(self):
        seeds = await self.start_urls()
        spider = ValidateSpider(
            name=self.name,
            seeds=seeds,
            check_urls=self.check_urls,
            parser_kls=self.parser_kls,
            # https://docs.python.org/zh-cn/3.10/library/typing.html#typing.cast
            error_handler=cast(Callable, functools.partial(self.error_handler)),
            pipeline_handler=functools.partial(self.save),
        )
        await spider.start()


async def main():
    task_manager = TaskManager()
    task_manager.load_task()
    task_manager.start()


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
