"""Settings"""
import dataclasses
import typing
from typing import Type

if typing.TYPE_CHECKING:
    from crawlerstack_proxypool.aio_scrapy.middlewares import \
        DownloadMiddleware


@dataclasses.dataclass
class Settings:
    """Settings"""
    download_middlewares: list[Type['DownloadMiddleware']] = dataclasses.field(default_factory=list)
    user_agent: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' \
                      ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'

    def __post_init__(self):
        """"""
