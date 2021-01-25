import logging
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Dict, Iterator, List, Optional, Tuple, Type

from pydantic.error_wrappers import ValidationError
from redis import Redis
from scrapy import Spider
from scrapy.crawler import Crawler, CrawlerRunner
from scrapy.settings import Settings
from scrapy.signalmanager import SignalManager
from twisted.internet import defer
from twisted.internet.defer import Deferred, maybeDeferred
from twisted.internet.task import LoopingCall

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.core.schemas import BaseTaskSchema
from crawlerstack_proxypool.dao.scene import redis_connect_pool


class StateCount:
    """
    任务的状态信息。
    用于记录任务在一个时间窗口中执行的次数，避免因为任务时间间隔设置有问题，导致任务密集执行
    """
    tasks_series: Dict[str, List] = {}  # 全局属性，具有单利特性。保存保存任务已经执行过的时间信息

    def __init__(self, time_window):
        """
        检测加载任务在一个时间窗口的运行次数
        抓取代理的任务时间窗口应该大一点，避免频繁抓取代理网站，导致不能用
        校验代理任务的时间窗口可以小一点，能事任务尽可能快的更新代理质量。但也不可以太快，会在校验时多度损耗代理IP
        此参数会影响任务配置中 `interval`。如果时间窗口较大，则 interval 的触发，不会运行实际逻辑
        :param time_window:
        """
        self.time_window = time_window
        self.task = LoopingCall(self.ttl)
        self.task.start(0.5)

    def stop(self):
        if self.task.running:
            self.task.stop()

    def mark(self, name):
        """
        记录任务运行时间，并保存
        :param name:
        :return:
        """
        now = datetime.now()
        time_series = self.tasks_series.get(name, None)
        if time_series is None:
            self.tasks_series.setdefault(name, [now])
        else:
            time_series.append(now)

    def ttl(self):
        """
        定期清理保存在内存中的任务执行时间信息
        :return:
        """
        before_one_minutes = datetime.now() - timedelta(seconds=self.time_window)
        # 遍历所有任务的信息
        for name, time_series in self.tasks_series.items():  # type: str, list
            # 遍历所有任务的时间信息，如果时间信息大于时间窗口，则清理
            for time in time_series:
                if time < before_one_minutes:
                    time_series.remove(time)

    def count(self, name: Optional[str] = None):
        # 获取任务在时间窗口中运行的次数
        data = deepcopy(self.tasks_series)
        return len(data.get(name, []))


class BaseTask:

    def __init__(self, signal: SignalManager):
        self._signal = signal
        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')

    def start(self) -> Deferred:
        raise NotImplementedError

    def stop(self) -> Deferred:
        raise NotImplementedError


class BaseSeedTask(BaseTask):
    task_key: str
    _once_fire_tasks: Dict[str, Deferred] = {}  # 具有单利性质
    _max_times = 1
    _interval_ratio = 10  # 任务 interval 数值的倍数
    time_window = settings.get('DEFAULT_TIME_WINDOW') or 60 * 5  # 检测加载任务在一个时间窗口的运行次数，会影响 interval
    task_schema: Type[BaseTaskSchema]

    def __init__(self, signal: SignalManager):
        super().__init__(signal)

        self._settings = settings
        self._state_count = StateCount(self.time_window)
        self._loop_tasks: Dict[str, LoopingCall] = {}

        self._tasks_config: List[BaseTaskSchema] = []
        for task_config in self._settings.get(self.task_key):
            task_config = self.task_schema(**task_config)
            if task_config.enable:
                self._tasks_config.append(task_config)

        self.__running: bool = False
        self.__closed: Optional[Deferred] = None
        self.client = Redis(connection_pool=redis_connect_pool)

    def processing(self, task_config: BaseTaskSchema) -> Optional[Deferred]:
        """
        运行任务
        即使任务通过 interval 自动触发，如果 time_window 时间内的运行次数大于 _max_times 实际逻辑也不会运行
        :param task_config:
        :return:
        """
        name = task_config.name
        count = self._state_count.count(name)
        self.logger.info(
            f'Processing {self.task_key} <{name}>, '
            f'interval: {task_config.interval}, '
            f'already processed {count} times.'
        )
        if count >= self._max_times:
            self.logger.warning(
                f'Processing {self.task_key} <{name}> more than {self._max_times} times between '
                f'{self._state_count.time_window} seconds, skip it.'
            )
        else:
            self.logger.info(f'Begin process {self.task_key} task <{name}>......')
            self._state_count.mark(name)  # 记录任务已经运行
            return maybeDeferred(self.load_seed, task_config)

    def load_seed(self, task_config: BaseTaskSchema) -> Optional[Deferred]:
        """
        执行任务的逻辑
        该方法可以是一个 Deferred。
        如果是有阻塞代码，建议返回 deferToThread
        :param task_config:
        :return:
        """
        raise NotImplementedError

    def _run_loop_task(self, task_config: BaseTaskSchema):
        """
        准备循环任务
        :param task_config:
        :return:
        """
        interval = task_config.interval
        name = task_config.name
        task = LoopingCall(self.processing, task_config)
        self._loop_tasks.setdefault(name, task)
        self.logger.info(f'Start {self.task_key} <{name}> loop run. interval: {interval * self._interval_ratio}')
        task.start(interval * self._interval_ratio)

    def _run_at_once(self, task_config: BaseTaskSchema) -> Optional[Deferred]:
        """
        Run once time.
        :param task_config:
        :return:
        """
        name = task_config.name
        if name in self._once_fire_tasks:
            self.logger.info(f'{self.task_key} <{name}> is running by trigger once, skip this trigger.')
        else:
            self.logger.info(f'Run {self.task_key} <{name}> once.')
            return self.processing(task_config)

    def load_tasks(self, once: bool = True, task_names: List[BaseTaskSchema] = ()) -> None:
        """
        加载任务，
        如果 once 为 True 则只运行一次任务。如果为 False 加载循环任务
        :param once:
        :param task_names:
        :return:
        """
        for task_config in self._tasks_config:
            # 如果 task_names 有值，但 task_config 的名称不在其中，则跳过此任务
            # 如果 task_names 中存在没有定义的任务，也是会跳过的
            # 如果 task_names 没有值，就会加载全部任务
            if task_names and task_config.name not in task_names:
                continue
            if once:
                self._run_at_once(task_config)
            else:
                self._run_loop_task(task_config)

    @property
    def running(self) -> bool:
        return self.__running

    def start(self) -> Deferred:
        self.logger.info(f'Start {self.task_key} ......')
        if self.__running:
            raise Exception('Task already running')
        self.__closed = defer.Deferred()
        self.__running = True
        self.load_tasks(False)

        return self.__closed

    def close(self):
        for name, task in self._loop_tasks.items():
            if task.running:
                task.stop()
                self.logger.info(f'Stop loop task <{name}>')

        self._state_count.stop()
        self.__closed.callback(None)

    def stop(self) -> Deferred:
        self.logger.info(f'Stop {self.task_key} ......')
        if self.__running:
            self.__running = False
            self.close()
            return self.__closed
        else:
            raise Exception('Task not running.')


class BaseCrawlerTask(BaseTask):
    """
    根据任务配置的信息加载 Spider 类，然后该每个 Spider 类创建 Crawler 用来运行 Spider 。
    在创建 Crawler 的时候，会读取任务配置中有没有 `customs_settings` ，用来创建 Crawler 是传入。
    """

    def __init__(self, signal: SignalManager):
        super().__init__(signal)

        self.logger = logging.getLogger(f'{__name__}.{self.__class__.__name__}')
        self.scrapy_settings = Settings()
        self.scrapy_settings.setdict(settings.as_dict())
        self.runner = CrawlerRunner(self.scrapy_settings)

    def load_crawl_config(self) -> Iterator[Tuple[Type[Spider], BaseTaskSchema]]:
        """
        加载 spider 类和该类的配置信息，然后调用 self.run_crawler 装在配置，启动爬虫。
        返回 Spider 类，和对应的数据模型对象的可迭代对象。生成器或者List
        :return:
        """
        raise NotImplementedError

    def _run_crawl(self):
        for spider_kls, task_config in self.load_crawl_config():
            try:
                self.logger.info(f'Start spider <{spider_kls}>, load config: {task_config}')
                # 传递一个创建的 Crawler 对象，目的是可以给 Crawler
                # 传入一个使用 task_config 中 customs_settings 修改的 settings
                self.runner.crawl(
                    crawler_or_spidercls=self._create_crawler(spider_kls, task_config),
                    name=task_config.name
                )
            except ValidationError as e:
                self.logger.error(f'Task config error. Task config : {task_config}. Reason: {e}')
                raise e

    def _create_crawler(self, spider_kls, task_config: BaseTaskSchema) -> Crawler:
        """
        使用 task_config 中的 customs_settings，修改 settings 然后创建新的 Crawler 。
        :param spider_kls:
        :param task_config:
        :return:
        """
        customs_settings = task_config.customs_settings
        scrapy_settings = self.scrapy_settings.copy()
        scrapy_settings.setdict(customs_settings)
        return Crawler(spider_kls, scrapy_settings)

    def start(self) -> Deferred:
        """
        Scrapy 内部会捕获 ctrl+c
        :return: 如果 runner 启动的所有爬虫完成，则返回的 Deferred 完成。
        """
        self.logger.info(f'Start {self.__class__.__name__} ......')
        self._run_crawl()
        return self.runner.join()

    def stop(self) -> Deferred:
        """
        手动停止所有 runner 启动的爬虫，停止抓取，并完成抓取之后的操作。
        :return:    如果所有爬虫完成，则返回的 Deferred 完成
        """
        self.logger.info(f'Stop {self.__class__.__name__} ......')
        return self.runner.stop()
