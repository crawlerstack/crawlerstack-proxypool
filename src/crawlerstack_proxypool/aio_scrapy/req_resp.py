"""request response proxy"""
import dataclasses
import typing

from httpx import URL
from httpx._client import UseClientDefault
from httpx._types import (AuthTypes, CookieTypes, HeaderTypes, ProxiesTypes,
                          QueryParamTypes, RequestContent, RequestData,
                          RequestFiles)


@dataclasses.dataclass(unsafe_hash=True, eq=False)
class RequestProxy:
    """
    Proxy httpx.Request
    """
    method: typing.Union[str, bytes]
    url: typing.Union[URL, str]
    _ = dataclasses.KW_ONLY
    params: QueryParamTypes = None
    headers: HeaderTypes = None
    cookies: CookieTypes = None
    content: RequestContent = None
    data: RequestData = None
    files: RequestFiles = None
    json: typing.Any = None
    extensions: dict = None
    proxy: ProxiesTypes = None
    auth: typing.Union[AuthTypes, UseClientDefault] = None
    follow_redirects: typing.Union[bool, UseClientDefault] = True
