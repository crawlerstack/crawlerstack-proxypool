"""common"""
import enum
import functools
from typing import Generic, Literal, cast

from crawlerstack_proxypool.common.extractor import (HtmlExtractor,
                                                     JsonExtractor)
from crawlerstack_proxypool.common.parser import BaseParser, ParserType
from crawlerstack_proxypool.common.validator import (AnonymousValidator,
                                                     BaseValidator,
                                                     KeywordValidator)


class BaseParserFactory(Generic[ParserType]):
    """
    抽象代理
    """

    parser_mapping: dict[str, ParserType] = {}

    def __init__(self):
        _mapping = self._init_parser_mapping()  # pylint: disable=assignment-from-no-return
        if _mapping:
            self.parser_mapping.update(_mapping)

    def _init_parser_mapping(self) -> dict[str, ParserType] | None:
        """"""

    def get_parser(self, name: str, **kwargs) -> ParserType:
        """
        工厂
        :return:
        """
        kls = self._get_parser_kls(name)
        # 使用告诫函数封装 from_params
        partial_parser = functools.partial(kls.from_params, **kwargs)
        return cast(ParserType, partial_parser)

    def _get_parser_kls(self, name: str) -> ParserType:
        kls = self.parser_mapping.get(name, None)
        if kls:
            return kls
        raise ValueError(f'{name} parser has not implement.')


class ExtractorFactory(BaseParserFactory[BaseParser]):
    """
    解析器代理
    """
    parser_mapping = {
        'html': HtmlExtractor,
        'json': JsonExtractor,
    }


class CheckerFactory(BaseParserFactory[BaseValidator]):
    """
    校验器代理
    """
    parser_mapping = {
        'keyword': KeywordValidator,
        'anonymous': AnonymousValidator,
    }


class ParserFactoryName(enum.Enum):
    """Parser Factory Name"""
    checker = 'checker'  # pylint: disable=invalid-name
    extractor = 'extractor'  # pylint: disable=invalid-name


_ParserFactoryNameType = Literal[ParserFactoryName.checker, ParserFactoryName.extractor]


class ParserFactoryProduce:
    """Parser Factory Produce"""
    factory = {
        ParserFactoryName.extractor: ExtractorFactory,
        ParserFactoryName.checker: CheckerFactory,
    }

    def get_factory(self, name: _ParserFactoryNameType):
        """get factory"""
        kls = self.factory.get(name)
        if kls:
            return kls()
        raise ValueError(f'Parser factory name not found: {name.value}.')
