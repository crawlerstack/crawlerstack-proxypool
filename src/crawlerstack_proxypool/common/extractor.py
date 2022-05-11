"""
Extractor
"""
import abc
import dataclasses
import ipaddress
import json
import logging
from typing import Type, TypeVar

from httpx import Response
from lxml import etree
from lxml.etree import Element

from crawlerstack_proxypool.aio_scrapy.spider import Spider

logger = logging.getLogger(__name__)


def proxy_check(ip_address: str, port: int) -> bool:
    """
    check whether the proxy ip and port are valid
    :param ip_address: proxy ip value
    :param port: proxy port value
    :return: True or False
    """
    try:
        ipaddress.ip_address(ip_address)
        _port = int(port)
        if _port > 65535 or _port <= 0:
            raise ValueError(f'Invalid port {port}')
    except ValueError:
        return False
    return True


@dataclasses.dataclass
class ExtractorKwargs:
    """
    Default extractor kwargs data class.
    """
    _ = dataclasses.KW_ONLY


ExtractorKwargsType = TypeVar('ExtractorKwargsType', bound=ExtractorKwargs)


class BaseExtractor(metaclass=abc.ABCMeta):
    """
    抽象 extractor 类
    """
    KWARGS_KLS: Type[ExtractorKwargsType] = ExtractorKwargs

    def __init__(self, spider: Spider):
        self.spider = spider
        self._kwargs = None

    @classmethod
    def from_kwargs(cls, spider: Spider, **kwargs):
        """
        从参数规范列表中初始化 extractor
        :param spider:
        :param kwargs:
        :return:
        """
        obj = cls(spider)
        obj.init_kwargs(**kwargs)
        return obj

    def init_kwargs(self, **kwargs):
        """
        使用参数初始化参数对象
        :param kwargs:
        :return:
        """
        self._kwargs = self.KWARGS_KLS(**kwargs)  # noqa

    @property
    def kwargs(self):
        """
        kwargs
        :return:
        """
        if self._kwargs is None:
            raise Exception(f'You should call {self.__class__}.init_kwargs to init kwargs first.')
        return self._kwargs

    @abc.abstractmethod
    async def parse(self, response: Response, **kwargs):
        """
        解析逻辑
        :param response:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()


ExtractorType = TypeVar('ExtractorType', bound=BaseExtractor)


@dataclasses.dataclass
class HtmlExtractorKwargs(ExtractorKwargs):
    """
    Html extractor 参数
    """
    rows_rule: str | None = '//tr'
    row_start: int | None = 1
    row_end: int | None = None
    columns_rule: str | None = 'td'
    ip_position: int | None = 0
    port_position: int | None = 1
    ip_rule: str | None = 'text()'
    port_rule: str | None = 'text()'


class HtmlExtractor(BaseExtractor):
    """
    html extractor
    """
    KWARGS_KLS: Type[HtmlExtractorKwargs] = HtmlExtractorKwargs

    async def parse(self, response: Response, **kwargs):
        html = etree.HTML(response.text)
        items = []
        rows = html.xpath(self._kwargs.rows_rule)[self._kwargs.row_start:]
        if self._kwargs.row_end is not None:
            rows = rows[:self._kwargs.row_end]

        for row in rows:
            row_html = row.get()
            if '透明' in row_html or 'transparent' in row_html.lower():
                continue
            proxy_ip = self.parse_row(row=row)
            if proxy_ip:
                items.append(proxy_ip)
        return items

    def parse_row(self, row: Element) -> str | None:
        """
        parse a row
        :param row:
        :return: 127.0.0.1:1080 / ''
        """
        try:
            proxy_ip = ''
            if self._kwargs.columns_rule:
                columns = row.xpath(self._kwargs.columns_rule)
                if columns:
                    _ip = columns[self._kwargs.ip_position]
                    proxy_ip = _ip.get()
                    if self._kwargs.ip_rule:
                        proxy_ip = _ip.xpath(self._kwargs.ip_rule).get()
                    if self._kwargs.port_position:
                        port = columns[self._kwargs.port_position]
                        port_str = port.get()
                        if self._kwargs.port_rule:
                            port_str = port.xpath(self._kwargs.port_rule).get()
                        proxy_ip = f'{proxy_ip}:{port_str}'
            else:
                proxy_ip = row.get()
            if proxy_ip and proxy_check(*proxy_ip.split(':')):
                return proxy_ip
        # I'm not sure if it's going to cause anything else.
        # But I want to avoid a problem that could cause a program to fail
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning(f'Parse row error %s. \n%s', ex, row.get())
        return None


@dataclasses.dataclass
class JsonExtractorKwargs:
    """
    Json extractor 参数
    """
    _ = dataclasses.KW_ONLY
    ip_key: str = 'ip'
    port_key: str = 'port'


class JsonExtractor(BaseExtractor):  # pylint: disable=too-few-public-methods
    """Json response extractor"""
    name = 'json'
    KWARGS_KLS = JsonExtractorKwargs

    async def parse(self, response: Response, **kwargs) -> list[str]:
        """
        parse json response.
        :param response: scrapy response
        :return: ip infos
        """
        infos = json.loads(response.text)
        items = []
        for info in infos:
            try:
                _ip = info.get(self._kwargs.ip_key)
                port = info.get(self._kwargs.port_key)
                if not proxy_check(_ip, port):
                    continue

                items.append(f'http://{_ip}:{port}')
                items.append(f'https://{_ip}:{port}')
            # I'm not sure if it's going to cause anything else.
            # But I want to avoid a problem that could cause a program to fail
            except Exception as ex:  # pylint: disable=broad-except
                logger.warning('Parse info error %s. \n%s', ex, info)

        return items
