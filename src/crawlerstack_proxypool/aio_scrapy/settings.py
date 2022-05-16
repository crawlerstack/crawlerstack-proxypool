"""Settings"""
import dataclasses
import typing
from typing import Type

if typing.TYPE_CHECKING:
    from crawlerstack_proxypool.aio_scrapy.middlewares import \
        DownloadMiddleware


@dataclasses.dataclass
class Settings:
    download_middlewares: list[Type['DownloadMiddleware']] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        """"""
