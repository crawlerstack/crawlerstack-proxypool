"""Parsers"""
import ipaddress
import json
from typing import TYPE_CHECKING, List, Optional, Union

from scrapy import Selector
from scrapy.http import HtmlResponse, Response

if TYPE_CHECKING:   # pragma: no cover
    from crawlerstack_proxypool.core.base import BaseSpider


def proxy_check(ip_addr: str, port: int) -> bool:
    """
    check whether the proxy ip and port are valid
    :param ip_addr: proxy ip value
    :param port: proxy port value
    :return: True or False
    """
    try:
        ipaddress.ip_address(ip_addr)
        _port = int(port)
        if _port > 65535 or _port <= 0:
            raise ValueError(f'Invalid port {port}')
    except ValueError:
        return False
    return True


class BaseParser:  # pylint: disable=too-few-public-methods
    """Base parser"""
    name: str = None

    def __init__(self, spider: 'BaseSpider'):
        # use log: self.spider.logger
        self.spider = spider

    def parse(self, *, response: Response, **kwargs) -> List[str]:  # pragma: no cover
        """
        Use parse rule to parse response and return ip.
        :param response:
        :return:    ['127.0.0.1:1080']
        """
        raise NotImplementedError('`parse()` must be implemented.')


class HtmlParser(BaseParser):
    """Parse html page"""
    name = 'html'

    def parse(  # pylint: disable=arguments-differ
            self,
            *,
            response: HtmlResponse,
            rows_rule: Optional[str] = '//tr',
            row_start: Optional[int] = 1,
            row_end: Optional[int] = None,
            columns_rule: Optional[str] = 'td',
            ip_position: Optional[int] = 0,
            port_position: Optional[int] = 1,
            ip_rule: Optional[str] = 'text()',
            port_rule: Optional[str] = 'text()',
    ) -> List[str]:
        """
        html response parser
        :param response: scrapy response
        :param rows_rule: extract rows rule
        :param row_start: row start offset. Include header row, header index is 0.
                        Default not include header row, you can set 0, to parse
                        first row.
        :param row_end: row end offset. If row_start and row_end is 0 and -1, all rows will use.
        :param columns_rule: extract ip and port rule. Then, if ip_rule or port_rule,
                        will use them to extract. If is None or '', will extract to text.
        :param ip_position: ip index
        :param port_position: port index. If is 0, port within ip eg: `127.0.0.1:1081`
        :param ip_rule: extract ip rule. Default `text()`, will use it extract from column.
        :param port_rule: extract port rule. Default `text()`,, will use it extract from column.
                If port_position is 0, it will not use.
        :return:    ['127.0.0.1:1080']
        """
        items = []
        rows = response.xpath(rows_rule)[row_start:]
        if row_end is not None:
            rows = rows[:row_end]

        for row in rows:
            row_html = row.get()
            if '透明' in row_html or 'transparent' in row_html.lower():
                continue
            proxy_ip = self.parse_row(
                row=row,
                columns_rule=columns_rule,
                ip_position=ip_position,
                port_position=port_position,
                ip_rule=ip_rule,
                port_rule=port_rule
            )
            if proxy_ip:
                items.append(proxy_ip)
        return items

    def parse_row(
            self,
            *,
            row: Union[Selector, str],
            columns_rule: Optional[str] = 'td',
            ip_position: Optional[int] = 0,
            port_position: Optional[int] = 1,
            ip_rule: Optional[str] = 'text()',
            port_rule: Optional[str] = 'text()',
    ) -> Optional[str]:
        """
        parse a row
        :param row:
        :param columns_rule:
        :param ip_position:
        :param port_position:
        :param ip_rule:
        :param port_rule:
        :return: 127.0.0.1:1080 / ''
        """
        try:
            proxy_ip = ''
            if columns_rule:
                columns = row.xpath(columns_rule)
                if columns:
                    _ip = columns[ip_position]
                    proxy_ip = _ip.get()
                    if ip_rule:
                        proxy_ip = _ip.xpath(ip_rule).get()
                    if port_position:
                        port = columns[port_position]
                        port_str = port.get()
                        if port_rule:
                            port_str = port.xpath(port_rule).get()
                        proxy_ip = f'{proxy_ip}:{port_str}'
            else:
                proxy_ip = row.get()
            if proxy_ip and proxy_check(*proxy_ip.split(':')):
                return proxy_ip
        # I'm not sure it's going to cause anything else.
        # But I want to avoid a problem that could cause a program to fail
        except Exception as ex:  # pylint: disable=broad-except
            self.spider.logger.warning(f'Parse row error {ex}. \n{row.get()}')
        return None


class JsonParser(BaseParser):  # pylint: disable=too-few-public-methods
    """Json response parser"""
    name = 'json'

    def parse(  # pylint: disable=arguments-differ
            self,
            *,
            response: Response,
            ip_key: Optional[str] = 'ip',
            port_key: Optional[str] = 'port'
    ) -> List[str]:
        """
        parse json response.
        :param response: scrapy response
        :param ip_key: ip extractor
        :param port_key: port extractor
        :return: ip infos
        """
        infos = json.loads(response.body.decode('utf-8'))
        items = []
        for info in infos:
            try:
                _ip = info.get(ip_key)
                port = info.get(port_key)
                if not proxy_check(_ip, port):
                    continue

                items.append(f'{_ip}:{port}')
            # I'm not sure it's going to cause anything else.
            # But I want to avoid a problem that could cause a program to fail
            except Exception as ex:  # pylint: disable=broad-except
                self.spider.logger.warning(f'Parse info error {ex}. \n{info}')

        return items


class TextParser(BaseParser):  # pylint: disable=too-few-public-methods
    """Text response parser"""
    name = 'text'

    def parse(  # pylint: disable=arguments-differ
            self,
            *,
            pre_extract: Optional[str] = None,
            response: Response,
            delimiter: Optional[str] = '\r\n',
            redundancy: Optional[str] = None,
    ) -> List[str]:
        """
        Raw response parser

        Example rule config:
            {
                'parser_name': 'text'
                'parser_rule':
                    {
                        'delimiter': "\r\n"
                        'redundancy': None
                    }
            }

        :param response: scrapy response
        :param pre_extract: per_extract from html, then parse plain text
        :param delimiter: split ip and port info from response
        :param redundancy: remove redundancy from ip info
        :return: ip infos
        """
        items = []
        if pre_extract:
            text = response.xpath(pre_extract).get()
        else:
            text = response.text
        infos: List[str] = text.split(delimiter)
        for info in infos:
            try:
                if redundancy:
                    info = info.replace(redundancy, '')
                if ':' not in info:
                    continue

                _ip, port = info.split(':')
                if not _ip or not port:
                    continue

                if not proxy_check(_ip, port):
                    continue

                items.append(f'{_ip}:{port}')
            # I'm not sure it's going to cause anything else.
            # But I want to avoid a problem that could cause a program to fail
            except Exception as ex:  # pylint: disable=broad-except
                self.spider.logger.warning(f'Parse info error {ex}. \n{info}')

        return items
