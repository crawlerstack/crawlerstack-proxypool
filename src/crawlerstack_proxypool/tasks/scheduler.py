import logging
from datetime import datetime, timedelta, tzinfo
from enum import Enum
from typing import Literal

import pydantic
import pytz
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pydantic import BaseModel

from crawlerstack_proxypool.common import (ParserFactoryName,
                                           ParserFactoryProduce)
from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.signals import (start_fetch_proxy,
                                            start_validate_proxy)
from crawlerstack_proxypool.tasks.fetcher import FetchSpiderTask
from crawlerstack_proxypool.tasks.validator import ValidateSpiderTask

logger = logging.getLogger(__name__)


class ParserConfig(BaseModel):
    name: str
    params: dict = {}


class TriggerName(Enum):
    cron = 'cron'
    interval = 'interval'
    date = 'date'


class IntervalTriggerConfig(BaseModel):
    weeks: int = 0
    days: int = 0
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    start_date: datetime | str = None
    end_date: datetime | str = None
    timezone: tzinfo | str = None
    jitter: int | None = None

    class Config:
        arbitrary_types_allowed = True


class CronTriggerConfig(BaseModel):
    year: int | None = None
    month: int = None
    day: int = None
    week: int = None
    day_of_week: int = None
    hour: int = None
    minute: int = None
    second: int = None
    start_date: datetime | str = None
    end_date: datetime | str = None
    timezone: tzinfo | str = None
    jitter: int | None = None

    class Config:
        arbitrary_types_allowed = True


class DateTriggerConfig(BaseModel):
    run_date: datetime | str = None
    timezone: tzinfo | str = None

    class Config:
        arbitrary_types_allowed = True


TRIGGER_TYPE = Literal['cron', 'interval', 'date']


class TriggerConfig(BaseModel):
    name: TRIGGER_TYPE
    params: dict

    @pydantic.validator('params')
    def params_check(cls, v, values) -> dict:  # noqa
        name = values.get('name')
        match name:
            case TriggerName.interval.value:
                config = IntervalTriggerConfig(**v)
            case TriggerName.cron.value:
                config = CronTriggerConfig(**v)
            case TriggerName.date.value:
                config = DateTriggerConfig(**v)
            case _:
                raise ValueError(f'Can not found trigger type: {name}')

        return config.dict()


class FetchTaskConfig(BaseModel):
    name: str
    urls: list[str]
    dest: list[str]
    parser: ParserConfig
    trigger: TriggerConfig


class ValidateTaskConfig(BaseModel):
    name: str
    urls: list[str]
    original: bool
    source: str
    dest: list[str]
    parser: ParserConfig
    trigger: TriggerConfig


class Scheduler:
    """
    任务管理。

    负责读取配置，创建爬虫任务，并加入到 apscheduler 进行调入。
    同时将对应的处理方法绑定到预定义事件上，在需要的时候，可以触发事件，
    让 apscheduler 立即调度对应的任务。
    """
    FETCH_TASK_NEXT_RUN_OFFSET = 5  # seconds
    VALIDATE_TASK_NEXT_RUN_OFFSET = 120  # seconds

    def __init__(self):
        """"""
        self.apscheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))

        self.fetch_jobs: list[tuple[str, Job]] = []
        self.validate_fetch_jobs: list[tuple[str, Job]] = []
        self.validate_scene_jobs: list[tuple[str, Job]] = []

        start_fetch_proxy.connect(self.trigger_fetch_job)
        start_validate_proxy.connect(self.trigger_validate_job)

        self.parser_factory_produce = ParserFactoryProduce()

    def load_task(self):
        """
        从配置中加载任务。

        :return:
        """
        fetch_task_config = settings.FETCH_TASK
        logger.debug('Loaded fetch task config from settings. Detail: %s', fetch_task_config)
        validate_task_config = settings.VALIDATE_TASK
        logger.debug('Loaded validate task config from settings. Detail: %s', validate_task_config)

        if fetch_task_config:
            self.load_fetch_task(fetch_task_config.to_list())
        if validate_task_config:
            self.load_validate_task(validate_task_config.to_list())

    def load_fetch_task(self, fetch_configs: list[dict]):
        """
        加载 fetch 任务。
        :param fetch_configs:
        :return:
        """
        for config_dict in fetch_configs:
            config = FetchTaskConfig(**config_dict)

            spider_task = FetchSpiderTask(
                name=config.name,
                urls=config.urls,
                parser_kls=self.parser_factory_produce.get_factory(
                    ParserFactoryName.extractor
                ).get_parser(
                    config.parser.name,
                    **config.parser.params
                ),
                dest=config.dest
            )
            logger.info(f'Loading spider task <{config.name}> . Task config: {config.json()}')

            next_run_time = datetime.now() + timedelta(seconds=self.FETCH_TASK_NEXT_RUN_OFFSET)
            task = self.apscheduler.add_job(
                func=spider_task.start,
                name=config.name,
                next_run_time=next_run_time,
                trigger=config.trigger.name,
                **config.trigger.params,
            )
            logger.info(
                f'Loaded spider task <{config.name} to scheduler. '
                f'Task id: {task.id}, next run time {next_run_time}>'
            )
            self.fetch_jobs.append((config.name, task))

    def load_validate_task(self, validate_configs: list[dict]):
        """load validate task"""
        for config_dict in validate_configs:
            config = ValidateTaskConfig(**config_dict)
            spider = ValidateSpiderTask(
                name=config.name,
                source=config.source,
                dest=config.dest,
                check_urls=config.urls,
                original=config.original,
                parser_kls=self.parser_factory_produce.get_factory(
                    ParserFactoryName.checker
                ).get_parser(
                    config.parser.name,
                    **config.parser.params
                ),
            )
            logger.info(f'Loading validate task <{config.name}> . Task config: {config.json()}')
            next_run_time = datetime.now() + timedelta(seconds=self.VALIDATE_TASK_NEXT_RUN_OFFSET)
            task = self.apscheduler.add_job(
                func=spider.start,
                name=config.name,
                next_run_time=next_run_time,
                trigger=config.trigger.name,
                **config.trigger.params,
            )
            logger.info(
                f'Loaded validate task <{config.name} to scheduler. '
                f'Task id: {task.id}, next run time {next_run_time}>'
            )
            if config.original:
                self.validate_fetch_jobs.append((config.name, task))
            else:
                self.validate_scene_jobs.append((config.name, task))

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
        logger.info('Starting scheduler.')
        self.apscheduler.start()

    def stop(self):
        """stop task manager"""
        logger.info('Stopping scheduler.')
        self.apscheduler.shutdown()


def trigger_job_run_now(job: Job):
    """
    触发任务。
    :param job:
    :return:
    """
    logger.info('Job "%s" run next time: %s, modifying run now.', job, job.next_run_time)
    job.modify(next_run_time=datetime.now() + timedelta(seconds=3))
