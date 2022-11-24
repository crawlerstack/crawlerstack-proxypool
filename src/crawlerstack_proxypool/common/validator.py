"""validator"""
import asyncio
import dataclasses
import random
from datetime import datetime, timedelta
from typing import TypeVar

from httpx import URL, Response

from crawlerstack_proxypool.aio_scrapy.downloader import DownloadHandler
from crawlerstack_proxypool.aio_scrapy.req_resp import RequestProxy
from crawlerstack_proxypool.aio_scrapy.spider import Spider
from crawlerstack_proxypool.common.parser import BaseParser, ParserParams
from crawlerstack_proxypool.schema import ValidatedProxy
from crawlerstack_proxypool.signals import spider_closed, spider_opened


class BaseValidator(BaseParser):
    """
    抽象校验器
    """

    async def parse(self, response: Response, **kwargs):
        return await self._check(response)

    async def _check(self, response: Response) -> ValidatedProxy:
        """
        检查逻辑
        :param response:
        :return:
        """
        raise NotImplementedError()

    def validated_proxy(self, url: URL, alive: bool):
        """validate proxy"""
        return ValidatedProxy(
            url=url,
            alive=alive,
            name=self.spider.name,
            source=self.spider.source,
            dest=self.spider.dest,
        )


_ValidatorType = TypeVar('_ValidatorType', bound=BaseValidator)  # pylint: disable=invalid-name


@dataclasses.dataclass
class KeywordValidatorParams(ParserParams):
    """
    关键字检查参数
    """
    keywords: list = dataclasses.field(default_factory=list)
    any: bool = False


class KeywordValidator(BaseValidator):
    """
    关键词校验器

    当抓取目标网站时，可以通过设置该站点必会出现的某个关键词（例如：国内网站底部都会有备案号）用来检查
    请求的结果是否存在关键词。如果存在则说明代理IP请求正常，否则请求异常。
call_args    """
    PARAMS_KLS = KeywordValidatorParams

    async def _check(self, response: Response) -> ValidatedProxy:
        checked = []
        for keyword in self.params.keywords:
            if keyword in response.text:
                checked.append(True)
            else:
                checked.append(False)

        if self.params.any:
            alive = any(checked)
        else:
            alive = all(checked)

        return self.validated_proxy(url=response.request.extensions.get('proxy'), alive=alive)


@dataclasses.dataclass
class AnonymousValidatorParams(ParserParams):
    """Anonymous params"""


class AnonymousValidator(BaseValidator):
    """
    匿名校验器

    原理：
        当请求一个网站时，目标服务器能从请求头中获取原始请求的公网IP地址。
    实现：
        通过访问一些能返回公网IP地址的站点（自己搭建或互联网的页面），得到当前本地公网IP。当通过代理IP请求该
        网站。如果两者的IP一致，则说明代理IP并没有起到代理的作用；如果不一致，则使用代理IP时伪装了实际公网IP，
        则说明该代理为匿名。
        对于非静态IP的宽带，需要注意IP是由运营商随机分配的，而且不定时改变，所以后台需要有轮询任务，间隔一定时间
        更新本地公网IP的值。

    """
    PARAMS_KLS = AnonymousValidatorParams

    def __init__(self, spider: Spider):
        super().__init__(spider)

        self._download_handler = DownloadHandler(spider.settings)
        self._internet_ip: str = ''
        self._refresh_ip_task: asyncio.Task | None = None
        self._running = False
        # 可以用信号绑定到 spider 上，也可以直接在 spider 的 open_spider 和 close_spider 中调用。
        spider_opened.connect(self.open_spider, sender=self.spider)
        spider_closed.connect(self.close_spider, sender=self.spider)

    @property
    def internet_ip(self) -> str:
        """
        本地公网IP，只是 IP 地址！
        :return: 88.88.88.88
        """
        return self._internet_ip

    async def open_spider(self, **_kwargs):
        """
        Run when spider opened.
        :param _kwargs:
        :return:
        """
        self._running = True
        loop = asyncio.get_running_loop()
        self._refresh_ip_task = loop.create_task(self.refresh_internet_ip())

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

    async def refresh_internet_ip(self):
        """
        间隔 10-20 秒中的随机数更新本地公网IP地址，用来判断代理IP识别的公网IP和本地公网IP是否一致。
        :return:
        """
        while self._running:
            await self.update_internet_ip()
            delay = random.randint(10, 20)
            trigger_time = datetime.now() + timedelta(seconds=delay)
            time_str = trigger_time.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
            self.spider.logger.debug(f'Next refresh internet ip: {time_str}.')
            await asyncio.sleep(delay)

    async def update_internet_ip(self):
        """
        获取最新当前公网IP，并更新变量
        :return:
        """
        try:
            request = RequestProxy(method='GET', url=URL('https://httpbin.iclouds.work/ip'))
            # response: "{"origin": "100.247.100.254"}"
            # response: "{"origin": "139.227.236.141, 123.13.247.40"}"
            response = await self._download_handler.download(request)
            ip = response.json().get('origin')
            self._internet_ip = ip
            self.spider.logger.debug(f'Update internet ip {self._internet_ip}.')
        except Exception as ex:
            self.spider.logger.exception(ex)
            # 如果下载出错，抛出异常，并关闭爬虫。
            await spider_closed.send(sender=self.spider)

    async def _check(self, response: Response):
        """
        检查本地公网 IP 是否在响应中。
        如果使用严格模式，还会检查配置的代理是否在响应中。
        :param response:
        :return:
        """
        if not self.internet_ip:
            raise ValueError('Internet ip value error.')
        alive = False
        proxy: URL = response.request.extensions.get('proxy')
        # 本地公网IP不在响应中，同时返回的响应中有代理IP.
        if self.internet_ip not in response.text and proxy.host in response.text:
            alive = True

        return self.validated_proxy(url=proxy, alive=alive)
