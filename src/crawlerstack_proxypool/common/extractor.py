"""
Extractor
"""
import dataclasses
import ipaddress
import json
import logging
from typing import Type

from httpx import Response
from lxml import etree
from lxml.etree import Element

from crawlerstack_proxypool.common.parser import BaseParser, ParserParams

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


# @dataclasses.dataclass
# class HtmlExtractorParams(ParserParams):
#     """
#     Html extractor 参数
#     """
#     rows_rule: str | None = '//tr'
#     row_start: int | None = 1
#     row_end: int | None = None
#     columns_rule: str | None = 'td'
#     ip_position: int | None = 0
#     port_position: int | None = 1
#     ip_rule: str = 'text()'
#     port_rule: str = 'text()'

class HtmlExtractorParams:

    def __init__(
            self,
            row_rule: str | None = '//tr',
            row_start: int | None = 1,
            row_end: int | None = None,
            columns_rule: str | None = 'td',
            ip_position: int | None = 0,
            port_position: int | None = 1,
            ip_rule: str = 'text()',
            port_rule: str = 'text()',
    ):
        self.row_rule = row_rule
        self.row_start = row_start
        self.row_end = row_end
        self.columns_rule = columns_rule
        self.ip_position = ip_position
        self.port_position = port_position
        self.ip_rule = ip_rule
        self.port_rule = port_rule


class HtmlExtractor(BaseParser):
    """
    html extractor
    """
    NAME = 'html'
    PARAMS_KLS: Type[HtmlExtractorParams] = HtmlExtractorParams

    async def parse(self, response: Response, **kwargs):
        html = etree.HTML(response.text)
        items = []
        rows = html.xpath(self._params.rows_rule)[self._params.row_start:]
        if self._params.row_end is not None:
            rows = rows[:self._params.row_end]

        for row in rows:
            row_html = etree.tostring(row).decode()
            if '透明' in row_html or 'transparent' in row_html.lower():
                continue
            proxy_ip = self.parse_row(row=row)
            if proxy_ip:
                items.extend(proxy_ip)
        return items

    def parse_row(self, row: Element) -> list[str] | None:
        """
        parse a row
        :param row:
        :return: 127.0.0.1:1080 / ''
        """
        row_html = etree.tostring(row).decode()
        try:
            proxy_ip = ''
            if self._params.columns_rule:
                columns = row.xpath(self._params.columns_rule)
                if columns:
                    _ip = columns[self._params.ip_position]
                    proxy_ip = _ip.xpath(self._params.ip_rule)[0]

                    if self._params.port_position:
                        port = self._extract_port(columns[self._params.port_position])
                        proxy_ip = f'{proxy_ip}:{port}'
            else:
                proxy_ip = row_html
            if proxy_ip and proxy_check(*proxy_ip.split(':')):
                return [
                    f'http://{proxy_ip}',  # noqa
                    f'https://{proxy_ip}'
                ]
        # I'm not sure if it's going to cause anything else.
        # But I want to avoid a problem that could cause a program to fail
        except Exception as ex:  # pylint: disable=broad-except
            logger.warning('Parse row error %s. \n%s', ex, row_html)
        return None

    def _extract_port(self, ele: Element) -> str:
        if self._params.port_rule:
            port_str = ele.xpath(self._params.port_rule)[0]
        else:
            port_str = ele.text
        return port_str


@dataclasses.dataclass
class JsonExtractorParams(ParserParams):
    """
    Json extractor 参数
    """
    _ = dataclasses.KW_ONLY
    ip_key: str = 'ip'
    port_key: str = 'port'


class JsonExtractor(BaseParser):  # pylint: disable=too-few-public-methods
    """Json response extractor"""
    NAME = 'json'
    PARAMS_KLS: Type[JsonExtractorParams] = JsonExtractorParams

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
                _ip = info.get(self._params.ip_key)
                port = info.get(self._params.port_key)
                if not proxy_check(_ip, port):
                    continue

                items.append(f'http://{_ip}:{port}')  # noqa
                items.append(f'https://{_ip}:{port}')
            # I'm not sure if it's going to cause anything else.
            # But I want to avoid a problem that could cause a program to fail
            except Exception as ex:  # pylint: disable=broad-except
                logger.warning('Parse info error %s. \n%s', ex, info)

        return items
