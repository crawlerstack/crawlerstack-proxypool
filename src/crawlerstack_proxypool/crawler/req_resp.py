import dataclasses
import json
import logging
from ssl import SSLContext
from typing import Any

from aiohttp import BasicAuth, ClientResponse, ClientTimeout
from yarl import URL

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class RequestProxy:
    method: str
    url: URL
    _: dataclasses.KW_ONLY = None
    params: dict[str, str] | None = None
    data: Any = None
    json: Any = None
    cookies: dict[str, str] | None = None
    headers: dict[str, str] | None = None

    auth: BasicAuth | None = None

    allow_redirects: bool = True
    max_redirects: int = 10

    compress: str | None = None

    proxy: URL | None = None
    proxy_auth: BasicAuth | None = None
    timeout: ClientTimeout | None = None

    fingerprint: bytes | None = None
    ssl_context: SSLContext | None = None
    ssl: bool | None = None

    read_bufsize: int | None = None  # noqa


@dataclasses.dataclass
class ResponseProxy:
    method: str
    url: URL
    text: str
    status: int
    headers: dict
    host: str
    request: RequestProxy

    @property
    def ok(self):
        return self.status < 400

    @property
    def json(self):
        return json.loads(self.text)

    @classmethod
    async def from_client_response(cls, response: ClientResponse, request: RequestProxy):
        text = await response.text()
        return cls(
            method=response.method,
            url=response.url,
            text=text,
            status=response.status,
            headers=dict(response.headers) if response.headers else {},
            host=response.host,
            request=request
        )
