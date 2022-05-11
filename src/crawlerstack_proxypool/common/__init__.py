from typing import Type, cast

from crawlerstack_proxypool.common.checker import (AnonymousChecker,
                                                   KeywordChecker)
from crawlerstack_proxypool.common.extractor import (BaseExtractor, HtmlExtractor,
                                                     JsonExtractor)


class ParserFactory:
    """
    解析器工厂
    """

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def get_extractor(self) -> Type[BaseExtractor]:
        """
        获取解析器
        :return:
        """
        return cast(Type[BaseExtractor], ExtractorParser(self.name, **self.kwargs))

    def get_checker(self) -> Type[BaseExtractor]:
        """
        获取校验器
        :return:
        """
        return cast(Type[BaseExtractor], CheckParser(self.name, **self.kwargs))


class Parser:
    """
    抽象代理
    """

    def __init__(self, name: str, **kwargs):
        self.kls = self.factory(name)
        self.kwargs = kwargs

    def factory(self, name: str):
        """
        工厂
        :param name:
        :return:
        """
        raise NotImplementedError()

    def __call__(self, *args, **kwargs) -> BaseExtractor:
        return self.kls.from_kwargs(*args, **kwargs, **self.kwargs)


class ExtractorParser(Parser):
    """
    解析器代理
    """

    def factory(self, name: str):
        if name == 'html':
            return HtmlExtractor
        if name == 'json':
            return JsonExtractor
        raise Exception(f'"{name}" parse has not implement.')


class CheckParser(Parser):
    """
    校验器代理
    """

    def factory(self, name: str):
        if name == 'keyword':
            return KeywordChecker
        if name == 'anonymous':
            return AnonymousChecker
        else:
            raise ValueError(f'Checker {name} has not implement.')
