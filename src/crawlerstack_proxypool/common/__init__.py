from typing import Type, cast

from crawlerstack_proxypool.common.checker import (AnonymousChecker,
                                                   KeywordChecker)
from crawlerstack_proxypool.common.parser import (BaseParser, HtmlParser,
                                                  JsonParser)


class ParserFactory:

    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs

    def get_parser(self) -> Type[BaseParser]:
        return cast(Type[BaseParser], ParserProxy(self.name, **self.kwargs))

    def get_checker(self) -> Type[BaseParser]:
        return cast(Type[BaseParser], CheckerProxy(self.name, **self.kwargs))


class BaseProxy:

    def __init__(self, name: str, **kwargs):
        self.kls = self.factory(name)
        self.kwargs = kwargs

    def factory(self, name: str):
        raise NotImplementedError()

    def __call__(self, *args, **kwargs) -> BaseParser:
        return self.kls.from_kwargs(*args, **kwargs, **self.kwargs)


class ParserProxy(BaseProxy):
    def factory(self, name: str):
        if name == 'html':
            return HtmlParser
        elif name == 'json':
            return JsonParser
        else:
            raise Exception(f'"{name}" parse has not implement.')


class CheckerProxy(BaseProxy):
    def factory(self, name: str):
        if name == 'keyword':
            return KeywordChecker
        elif name == 'anonymous':
            return AnonymousChecker
        else:
            raise ValueError(f'Checker {name} has not implement.')
