import typing

from httpx import Response

from crawlerstack_proxypool.crawler import Spider


class ValidateSpider(Spider):

    def __init__(
            self,
            *,
            name: str,
            start_urls: list[str],
            check_urls: list[str]
    ):
        super().__init__(name=name, start_urls=start_urls)
        self.check_urls = check_urls

    async def parse(self, response: Response) -> typing.Any:
        pass
