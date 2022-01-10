import dataclasses
import ipaddress
import json
import logging
from typing import Type, TypeVar

from lxml import etree
from lxml.etree import Element

from crawlerstack_proxypool.crawler.req_resp import ResponseProxy
from crawlerstack_proxypool.crawler.spider import BaseParser as SpiderParser, Spider

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
class ParserKwargs:
    """
    Default parse kwargs data class.
    """
    _ = dataclasses.KW_ONLY


_KwargsType = TypeVar('_KwargsType', bound=ParserKwargs)


class BaseParser(SpiderParser):
    KWARGS_KLS: Type[_KwargsType] = ParserKwargs

    def __init__(self, spider: Spider):
        super().__init__(spider)
        self._kwargs = None

    @classmethod
    def from_kwargs(cls, spider: Spider, **kwargs):
        obj = cls(spider)
        obj.init_kwargs(**kwargs)
        return obj

    def init_kwargs(self, **kwargs):
        self._kwargs = self.KWARGS_KLS(**kwargs)  # noqa

    @property
    def kwargs(self):
        if self._kwargs is None:
            raise Exception(f'You should call {self.__class__}.init_kwargs to init kwargs first.')
        return self._kwargs

    async def parse(self, response: ResponseProxy, **kwargs):
        raise NotImplementedError()


@dataclasses.dataclass
class HtmlParserKwargs(ParserKwargs):
    rows_rule: str | None = '//tr',
    row_start: int | None = 1,
    row_end: int | None = None,
    columns_rule: str | None = 'td',
    ip_position: int | None = 0,
    port_position: int | None = 1,
    ip_rule: str | None = 'text()',
    port_rule: str | None = 'text()',


class HtmlParser(BaseParser):
    KWARGS_KLS: Type[HtmlParserKwargs] = HtmlParserKwargs

    async def parse(self, response: ResponseProxy, **kwargs):
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
            logger.warning(f'Parse row error {ex}. \n{row.get()}')
        return None


@dataclasses.dataclass
class JsonParserKwargs:
    _ = dataclasses.KW_ONLY
    ip_key: str = 'ip'
    port_key: str = 'port'


class JsonParser(BaseParser):  # pylint: disable=too-few-public-methods
    """Json response parser"""
    name = 'json'
    KWARGS_KLS = JsonParserKwargs

    async def parse(self, response: ResponseProxy, **kwargs) -> list[str]:
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
                logger.warning(f'Parse info error {ex}. \n{info}')

        return items
