"""Checkers"""
import json
from typing import TYPE_CHECKING

from scrapy import Request, signals
from scrapy.core.downloader.handlers.http11 import HTTP11DownloadHandler
from scrapy.http import Response
from twisted.internet import defer
from twisted.internet.task import LoopingCall

if TYPE_CHECKING:  # pragma: no cover
    from crawlerstack_proxypool.spiders.scene import SceneSpider


class BaseChecker:  # pylint: disable=too-few-public-methods
    """Base checker"""
    name = 'base'

    def __init__(self, spider: 'SceneSpider'):
        self.spider = spider

    def check(self, *, response: Response, **kwargs):  # pragma: no cover
        """Check response"""
        raise NotImplementedError


class AnonymousChecker(BaseChecker):  # pylint: disable=too-few-public-methods
    """
    Anonymous checker. To check proxy ip is anonymous.
    First, access to the local public network IP,
    if the use of proxy access IP and the local public network IP is the same,
    this proxy IP is not anonymous.
    """
    name = 'anonymous'
    origin: str = ''  # origin ip address
    http_check_url = 'https://httpbin.org/ip'
    update_local_public_ip_interval = 60 * 5
    _MAX_REFRESH_ERROR_TIMES = 20
    _refresh_error_times = 0

    def __init__(self, spider: 'SceneSpider'):
        super().__init__(spider)
        self.logger = spider.logger
        self.__downloader = HTTP11DownloadHandler(
            settings=spider.settings, crawler=spider.crawler
        )
        self.__loop_check_ip_task = LoopingCall(self.__refresh_publish_ip)
        # Update local public ip every x seconds.
        self.__loop_check_ip_task.start(self.update_local_public_ip_interval)
        self.spider.crawler.signals.connect(self._spider_closed, signals.spider_closed)

    @defer.inlineCallbacks
    def _spider_closed(self):
        """When spider close, stop task."""
        if self.__loop_check_ip_task.running:
            self.__loop_check_ip_task.stop()
        yield self.__downloader.close()

    @defer.inlineCallbacks
    def __refresh_publish_ip(self):
        """Obtain local public ip addr"""
        request = Request(url=self.http_check_url)
        try:
            self._refresh_error_times = 0
            resp = yield self.__downloader.download_request(request, spider=self.spider)
            json_obj = json.loads(resp.text)
            self.origin = json_obj.get('origin')
            self.logger.debug(f'Refresh {self.spider} origin ip {self.origin} success.')
        except Exception as ex:
            self._refresh_error_times += 1
            self.logger.error(f'{self} refresh publish ip error. {ex}')
            if self._refresh_error_times >= self._MAX_REFRESH_ERROR_TIMES:
                self.spider.crawler.engine.close_spider(
                    self.spider,
                    reason='Checker max refresh publish ip error.'
                )

    def check(self, *, response: Response, **kwargs) -> bool:
        """
        Filter transparent ip resources

        If proxy ip is transparent, response will content host public ip
        {
          "origin": "139.227.236.141, 123.13.247.40"
        }
        """
        if self.origin:
            # If local public IP in response use by Proxy ip, is transparent
            if self.origin in response.text:
                return False
            return True
        raise Exception(
            f"Local public IP is invalid. <{self.origin}>, "
            f"Can't check if the proxy ip anonymous."
        )


class KeyWordsChecker(BaseChecker):  # pylint: disable=too-few-public-methods
    """Keyword checker"""
    name = 'keywords'

    def check(  # pylint: disable=arguments-differ
            self,
            *,
            response: Response,
            keywords=(),
            strict=False,
    ) -> bool:
        """
        Check key work in response, if check one of key words, return True.
        :param response:
        :param keywords:
        :param strict:  If true, all keywords will be found.
        :return:
        """
        checked = []
        for key_word in keywords:
            if key_word in response.text:
                checked.append(True)
            else:
                checked.append(False)
        if strict:
            result = all(checked)
        else:
            result = any(checked)
        return result
