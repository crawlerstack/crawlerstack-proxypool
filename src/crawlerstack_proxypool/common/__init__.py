from typing import Type, cast

from crawlerstack_proxypool.common.checker import (AnonymousChecker,
                                                   KeywordChecker)
from crawlerstack_proxypool.common.parser import (BaseParser, HtmlParser,
                                                  JsonParser)


class ParserFactory:
    """
    解析器工厂
    """

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def get_parser(self) -> Type[BaseParser]:
        """
        获取解析器
        :return:
        """
        return cast(Type[BaseParser], ParserProxy(self.name, **self.kwargs))

    def get_checker(self) -> Type[BaseParser]:
        """
        获取校验器
        :return:
        """
        return cast(Type[BaseParser], CheckerProxy(self.name, **self.kwargs))


class BaseProxy:
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

    def __call__(self, *args, **kwargs) -> BaseParser:
        return self.kls.from_kwargs(*args, **kwargs, **self.kwargs)


class ParserProxy(BaseProxy):
    """
    解析器代理
    """
    def factory(self, name: str):
        if name == 'html':
            return HtmlParser
        if name == 'json':
            return JsonParser
        raise Exception(f'"{name}" parse has not implement.')


class CheckerProxy(BaseProxy):
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
