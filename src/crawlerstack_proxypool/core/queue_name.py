from scrapy import Spider

from crawlerstack_proxypool.utils.constants import QUEUE_PREFIX

# pylint: disable=too-few-public-methods

class QueueName:

    def __init__(self, spider_or_name):
        if isinstance(spider_or_name, Spider):
            self._spider_name = spider_or_name.name
        else:
            self._spider_name = spider_or_name

    def _connect(self, name):
        """Connect name"""
        return f'{QUEUE_PREFIX}:{self._spider_name}:{name}'


class PageQueueName(QueueName):
    """
    eg: ajax seed queue ====> `crawlerstack_proxypool:spider:ajax:seed`
    """

    @property
    def seed(self):
        """Seed name"""
        return self._connect('seed')

    def _connect(self, name):
        """Connect name"""
        return f'{QUEUE_PREFIX}:raw:{self._spider_name}:{name}'


class SceneQueueName(QueueName):
    """
    Scene task queue
    """

    @property
    def time(self):
        """last test time"""
        return self._connect('time')

    @property
    def speed(self):
        """Time interval between request and response."""
        return self._connect('speed')

    @property
    def score(self):
        """
        When this ip is not available， decrease core, otherwise, increase score.
        When score is less than 1, this ip will remove.
        :return:
        """
        return self._connect('score')

    @property
    def seed(self):
        """Seed name"""
        return self._connect('seed')

    @property
    def verify(self):
        """customs check urls queue"""
        return self._connect('verify')
