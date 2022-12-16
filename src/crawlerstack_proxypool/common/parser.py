"""parser"""
import abc
import dataclasses
from typing import Generic, Type, TypeVar

from httpx import Response

from crawlerstack_proxypool.spiders import Spider


@dataclasses.dataclass
class ParserParams:
    """
    Default parser kwargs data class.
    """
    _ = dataclasses.KW_ONLY


ParserParamsType = TypeVar('ParserParamsType', bound=ParserParams)  # pylint: disable=invalid-name


class BaseParser(Generic[ParserParamsType]):
    """
    抽象 parser 类
    """
    NAME: str
    PARAMS_KLS: Type[ParserParamsType] = ParserParams

    def __init__(self, spider: Spider):
        self.spider = spider
        self._params = None

    @classmethod
    def from_params(cls, /, spider: Spider, **kwargs):
        """
        从参数规范列表中初始化 Parser
        :param spider:
        :param kwargs:
        :return:
        """
        obj = cls(spider)
        obj.init_params(**kwargs)
        return obj

    def init_params(self, **kwargs):
        """
        使用参数初始化参数对象
        :param kwargs:
        :return:
        """
        self._params = self.PARAMS_KLS(**kwargs)  # noqa

    @property
    def params(self) -> ParserParamsType:
        """
        kwargs
        :return:
        """
        if self._params is None:
            raise Exception(f'You should call {self.__class__}.init_params to init params first.')
        return self._params

    @abc.abstractmethod
    async def parse(self, response: Response, **kwargs):
        """
        解析逻辑
        :param response:
        :param kwargs:
        :return:
        """
        raise NotImplementedError()


ParserType = TypeVar('ParserType', bound=BaseParser)  # pylint: disable=invalid-name
