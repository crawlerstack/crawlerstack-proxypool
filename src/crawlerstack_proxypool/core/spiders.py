"""Spiders"""
from typing import Iterable, Optional

from redis import Redis
from scrapy import Request, Spider, signals
from scrapy.crawler import Crawler
from scrapy.exceptions import DontCloseSpider


class RedisSpider(Spider):  # pylint: disable=abstract-method
    """
    Redis spider
    This is abstract spider, you should impl RedisSpider.parse method.
    """

    server: Redis = None
    redis_batch_size: int = None
    redis_key: str = None

    def _set_crawler(self, crawler: Crawler) -> None:
        super()._set_crawler(crawler)
        self._setup_redis(crawler)

    def _setup_redis(self, crawler: Optional[Crawler] = None) -> None:
        """Setup redis"""

        crawler = crawler or getattr(self, 'crawler', None)
        if not crawler:
            raise AttributeError(f'{self.__class__.__name__} not have "crawler"')

        # The idle signal is called when the spider has no requests left,
        # that's when we will schedule new requests from redis queue
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

        if self.redis_key is None:
            self.redis_key = self.name

        # When REDIS_START_URL_BATCH_SIZE is None, will use CONCURRENT_REQUESTS.
        if self.redis_batch_size is None:
            self.redis_batch_size = crawler.settings.getint(
                'REDIS_START_URL_BATCH_SIZE',
                crawler.settings.getint('CONCURRENT_REQUESTS')
            )

        self.logger.info(
            f"To read start URLs from redis key {self.redis_key}'"
            f"(batch size: {self.redis_batch_size})"
        )
        if self.server is not None:
            return

        self.server = Redis.from_url(crawler.settings.get('REDIS_URL'), decode_responses=True)

    def start_requests(self) -> Iterable[Request]:
        """Start requests"""
        return self.next_requests()

    def next_requests(self) -> Iterable[Request]:
        """Next requests, to fetch data from redis, and yield request object."""
        use_set = self.settings.getbool('REDIS_START_URL_AS_SET')
        fetch_one = self.server.spop if use_set else self.server.lpop
        found = 0
        while found < self.redis_batch_size:
            data = fetch_one(self.redis_key)
            if not data:
                # Queue empty.
                break
            req = self.make_request_from_url(data)
            if req:
                yield req
                found += 1
            else:
                self.logger.debug(f'Request not made from data: {data}')

        if found:
            self.logger.debug(f'Read {found} requests from {self.redis_key}')

    def make_request_from_url(self, url: str) -> Request:  # pylint: disable=no-self-use
        """
        Make request from url.

        You can override it instead of override self.next_requests,
        to customs how to do you generate Request
        :param url:
        :return:
        """
        return Request(url, dont_filter=True)

    def schedule_next_requests(self) -> None:
        """Schedules a request if available"""
        for req in self.next_requests():
            self.crawler.engine.crawl(req, spider=self)

    def spider_idle(self) -> None:
        """Schedules a request if available, otherwise waits."""
        self.schedule_next_requests()
        raise DontCloseSpider
