"""
Task
"""
import asyncio
import dataclasses
import logging
from datetime import datetime, timedelta
from typing import Type

import pytz
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from httpx import URL
from sqlalchemy.ext.asyncio import AsyncSession

from crawlerstack_proxypool.aio_scrapy.crawler import Crawler
from crawlerstack_proxypool.common import BaseExtractor, ParserFactory
from crawlerstack_proxypool.common.checker import CheckedProxy
from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.db import session_provider
from crawlerstack_proxypool.service import (FetchSpiderService,
                                            ValidateSpiderService)
from crawlerstack_proxypool.signals import (start_fetch_proxy,
                                            start_validate_proxy)
from crawlerstack_proxypool.spiders import Spider, ValidateSpider

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
        logger.debug('Loaded fetch task config from settings. Detail: %s', fetch_task_config)
        validate_task_config = settings.get('validate_task')
        logger.debug('Loaded validate task config from settings. Detail: %s', validate_task_config)

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
            parser = config['extractor']
            schedule = config['schedule']
            spider = FetchSpiderTask(
                name=name,
                urls=config['urls'],
                parser_kls=ParserFactory(**parser).get_extractor(),
                dest=config['dest']
            )
            task = self.scheduler.add_job(
                func=spider.start,
                name=name,
                next_run_time=datetime.now() + timedelta(seconds=5),
                **schedule,
            )
            self.fetch_jobs.append((name, task))

    def load_validate_task(self, validate_config: dict):
        """load validate task"""
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
                self.validate_scene_jobs.append((name, task))
            else:
                self.validate_fetch_jobs.append((name, task))

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
            for name, job in self.validate_scene_jobs:
                if name in sources:
                    trigger_job_run_now(job)
        else:
            for _, job in self.validate_fetch_jobs:
                trigger_job_run_now(job)

    def start(self):
        """start task manager"""
        logger.info('Starting task manage.')
        self.scheduler.start()

    def stop(self):
        """stop task manager"""
        logger.info('Stopping task manage.')
        self.scheduler.shutdown()


def trigger_job_run_now(job: Job):
    """
    触发任务。
    :param job:
    :return:
    """
    logger.debug('Job "%s" run next time: %s, modifying run now.', job, job.next_run_time)
    job.modify(next_run_time=datetime.now() + timedelta(seconds=3))


@dataclasses.dataclass
class FetchSpiderTask:
    """
    Fetch spider task
    """
    name: str
    urls: list[str]
    dest: list[str]
    parser_kls: Type[BaseExtractor] | None = None

    async def start_urls(self):
        """start urls"""
        for url in self.urls:
            yield URL(url)

    @session_provider(auto_commit=True)
    async def save(self, proxy: list[URL], session: AsyncSession):
        """save"""
        service = FetchSpiderService(session)
        await service.save(proxy, self.dest)

    async def start(self):
        """start task"""
        crawler = Crawler(Spider)
        await crawler.crawl(
            name=self.name,
            start_urls=self.start_urls(),
            parser_kls=self.parser_kls,
            pipeline=self.save
        )


@dataclasses.dataclass
class ValidateSpiderTask:
    """Validate spider task"""
    name: str
    dest: str
    check_urls: list[str]
    parser_kls: Type[BaseExtractor] | None = None
    sources: list[str] | None = dataclasses.field(default_factory=list)

    @session_provider(auto_commit=True)
    async def start_urls(self, session: AsyncSession):
        """
        :param session:
        :return:
        """
        service = ValidateSpiderService(session)
        return await service.start_urls(self.dest, self.sources)

    @session_provider(auto_commit=True)
    async def save(self, proxy: CheckedProxy, session: AsyncSession):
        """
        不需要将 service = ValidateService(session) 提取出来。因为 save 任务传递到
        ValidateSpider 会放到一个 task 中运行，使用 session_provider 自动管理该 task 中的 session 生命周期。
        :param proxy:
        :param session:
        :return:
        """
        service = ValidateSpiderService(session)
        await service.save(proxy, self.dest)

    async def start(self):
        """start task"""
        seeds = await self.start_urls()
        crawler = Crawler(ValidateSpider)
        await crawler.crawl(
            name=self.name,
            start_urls=seeds,
            check_urls=self.check_urls,
            parser_kls=self.parser_kls,
            pipeline=self.save
        )


async def main():
    task_manager = TaskManager()
    task_manager.load_task()
    task_manager.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)
    loop = asyncio.new_event_loop()
    loop.create_task(main())
    loop.run_forever()
