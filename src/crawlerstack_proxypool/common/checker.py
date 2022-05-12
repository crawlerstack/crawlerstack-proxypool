import asyncio
import dataclasses
import random
from typing import TypeVar

from httpx import URL, Response

from crawlerstack_proxypool.common.extractor import BaseExtractor, ExtractorKwargs
from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.aio_scrapy.spider import Spider


@dataclasses.dataclass
class CheckedProxy:
    """
    已经检查过的 proxy 对象
    """
    url: URL
    alive: bool
    alive_status: int = dataclasses.field(default=None)

    def __post_init__(self):
        if self.alive:
            self.alive_status = 1
        else:
            self.alive_status = -1


class BaseChecker(BaseExtractor):
    """
    抽象校验器
    """

    async def parse(self, response: Response, **kwargs):
        return await self.check(response)

    async def check(self, response: Response) -> CheckedProxy:
        """
        检查逻辑
        :param response:
        :return:
        """
        raise NotImplementedError()


_CheckerType = TypeVar('_CheckerType', bound=BaseChecker)


@dataclasses.dataclass
class KeywordCheckKwargs(ExtractorKwargs):
    """
    关键字检查参数
    """
    keywords: list = dataclasses.field(default_factory=list)
    any: bool = False


class KeywordChecker(BaseChecker):
    """
    关键词校验器

    当抓取目标网站时，可以通过设置该站点必会出现的某个关键词（例如：国内网站底部都会有备案号）用来检查
    请求的结果是否存在关键词。如果存在则说明代理IP请求正常，否则请求异常。
    """
    KWARGS_KLS = KeywordCheckKwargs

    async def check(self, response: Response) -> CheckedProxy:
        alive = False
        if response.status_code == 200:
            if self.check_keywords(response.text):
                alive = True

        return CheckedProxy(url=response.request.headers.get('proxy'), alive=alive)

    def check_keywords(self, text: str) -> bool:
        """
        检查文本中是否包含官监察。
        :param text:
        :return:
        """
        checked = []
        for keyword in self.kwargs.keywords:
            if keyword in text:
                checked.append(True)
            else:
                checked.append(False)
        if self.kwargs.any:
            return any(checked)
        return all(checked)


@dataclasses.dataclass
class AnonymousKwargs(ExtractorKwargs):
    """
    严格模式。
    """
    strict: bool = False


class AnonymousChecker(BaseChecker):
    """
    匿名校验器

    原理：
        当请求一个网站时，目标服务器能从请求头中获取原始请求的公网IP地址。
    实现：
        通过访问一些能返回公网IP地址的站点（自己搭建或互联网的页面），得到当前本地公网IP，然后再通过代理IP请求该
        网站。如果两者的IP一致，则说明代理IP并没有起到代理的作用；如果不一致，则使用代理IP时伪装了实际公网IP，
        则说明该代理为匿名。
        对于非静态IP的宽带，需要注意IP是由运营商随机分配的，而且不定时改变，所以后台需要有轮询任务，间隔一定时间
        更新本地公网IP的值。

    """
    KWARGS_KLS = AnonymousKwargs

    def __init__(self, spider: Spider):
        """"""
        super().__init__(spider)

        self._download_handler = DownloadHandler()
        self._public_ip = ''
        self._refresh_ip_task: asyncio.Task | None = None
        self._running = False
        # 可以用信号绑定到 spider 上，也可以直接在 spider 的 open_spider 和 close_spider 中调用。
        # spider_opened.connect(self.open_spider, sender=self.spider)
        # spider_closed.connect(self.close_spider, sender=self.spider)

    async def open_spider(self, **_kwargs):
        """
        Run when spider opened.
        :param _kwargs:
        :return:
        """
        self._running = True
        loop = asyncio.get_running_loop()
        self._refresh_ip_task = loop.create_task(self.refresh_public_ip())

    async def close_spider(self, **_kwargs):
        """
        Run when spider closed.
        :param _kwargs:
        :return:
        """
        self._running = False
        await asyncio.sleep(0)
        self._refresh_ip_task.cancel()
        await self._download_handler.close()

    async def refresh_public_ip(self):
        """
        间隔 10-20 秒中的随机数更新本地公网IP地址，用来判断代理IP识别的公网IP和本地公网IP是否一致。
        :return:
        """
        while self._running:
            await self.get_public_ip()
            delay = random.randint(10, 20)
            await asyncio.sleep(delay)

    async def get_public_ip(self):
        """
        获取最新当前公网IP，并更新变量
        :return:
        """
        request = RequestProxy(method='GET', url=URL('https://httpbin.iclouds.work/ip'))
        # response: "{"origin": "100.247.100.254"}"
        # response: "{"origin": "139.227.236.141, 123.13.247.40"}"
        response = await self._download_handler.download(request)
        self._public_ip = response.json().get('origin')
        self.spider.logger.debug(f'Refresh public ip: "{self._public_ip}"')

    async def check(self, response: Response):
        """
        检查本地公网 IP 是否在响应中。
        如果使用严格模式，还会检查配置的代理是否在响应中。
        :param response:
        :return:
        """
        if not self._public_ip:
            await self.get_public_ip()
        alive = False
        proxy: URL = response.request.extensions.get('proxy')
        if response.status_code:
            if self._public_ip not in response.text:
                if self.kwargs.strict and proxy.host in response.text:
                    alive = True
                else:
                    alive = True
        return CheckedProxy(url=proxy, alive=alive)
