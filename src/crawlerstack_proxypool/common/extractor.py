"""
Extractor
"""
import dataclasses
import ipaddress
import json
import logging
from abc import ABC
from typing import Generic, Type

from httpx import URL, Response
from lxml import etree
from lxml.etree import Element

from crawlerstack_proxypool.common.parser import (BaseParser, ParserParams,
                                                  ParserParamsType)

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
            raise ValueError(f'Invalid port: {port}')
    except ValueError:
        return False
    return True


class BaseExtractor(BaseParser, Generic[ParserParamsType], ABC):
    """
    抽象校验器
    """

    ALLOW_SCHEMA = ['http', 'https']

    def build_proxies(self, ip: str, port: int) -> list[URL]:
        """build proxies"""
        proxies = []
        if proxy_check(ip, port):
            for schema in self.ALLOW_SCHEMA:
                proxies.append(URL(f'{schema}://{ip}:{port}'))
        return proxies


@dataclasses.dataclass
class HtmlExtractorParams(ParserParams):
    """
    Html extractor 参数

    :param rows_rule: 表格行提取规则，默认是 `//tr` 即表格的行标签。
    :param row_start: 行其实索引位置，默认是 1 即去除表头。
    :param row_end: 行结束位置，默认，默认是 -1 即去除表格底部的翻页标签。
    :param columns_rule: 行中的列提取规则。
    :param ip_position: IP 在列中的索引位置，默认是第一列，即索引为 0，
    :param port_position: 端口在列中的索引位置，默认为第二列，即索引为 1。
    :param ip_rule: IP 提取规则。
    :param port_rule: 端口提取规则。

    """
    rows_rule: str | None = '//tr'
    row_start: int | None = 1
    row_end: int | None = -1
    columns_rule: str | None = 'td'
    ip_position: int | None = 0
    port_position: int | None = 1
    ip_rule: str = 'text()'
    port_rule: str = 'text()'


class HtmlExtractor(BaseExtractor[HtmlExtractorParams]):
    """
    html extractor
    """
    NAME = 'html'
    PARAMS_KLS: Type[HtmlExtractorParams] = HtmlExtractorParams

    async def parse(self, response: Response, **kwargs) -> list[URL]:
        html = etree.HTML(response.text)
        items = []
        rows = html.xpath(self._params.rows_rule)[self._params.row_start:self._params.row_end]

        for row in rows:
            row_html = etree.tostring(row).decode()  # pylint: disable=
            if '透明' in row_html or 'transparent' in row_html.lower():
                continue
            items.extend(self.parse_row(row=row))
        return items

    def parse_row(self, row: Element) -> list[URL] | None:
        """
        parse a row
        :param row:
        :return: 127.0.0.1:1080 / ''
        """
        row_html = etree.tostring(row).decode()
        try:
            columns = row.xpath(self._params.columns_rule)
            if columns:
                ip_ele = columns[self._params.ip_position]
                ip = ip_ele.xpath(self._params.ip_rule)[0]

                if self._params.port_position:
                    port_ele = columns[self._params.port_position]
                    port = port_ele.xpath(self._params.port_rule)[0]
                else:
                    ip, port = ip.split(':')
                return self.build_proxies(ip, port)

        # I'm not sure if it's going to cause anything else.
        # But I want to avoid a problem that could cause a program to fail
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning('Parse row error %s. \n%s', ex, row_html)
        return None


@dataclasses.dataclass
class JsonExtractorParams(ParserParams):
    """
    Json extractor 参数
    """
    _ = dataclasses.KW_ONLY
    ip_key: str = 'ip'
    port_key: str = 'port'


class JsonExtractor(BaseExtractor):  # pylint: disable=too-few-public-methods
    """Json response extractor"""
    NAME = 'json'
    PARAMS_KLS: Type[JsonExtractorParams] = JsonExtractorParams

    async def parse(self, response: Response, **kwargs) -> list[URL]:
        """
        parse json response.
        :param response: scrapy response
        :return: ip infos
        """
        infos = json.loads(response.text)
        items = []
        for info in infos:
            ip = info.get(self._params.ip_key)
            port = info.get(self._params.port_key)
            if not proxy_check(ip, port):
                continue
            items.extend(self.build_proxies(ip, port))

        return items
