"""schema"""
from httpx import URL
from pydantic import BaseModel, validator


class SceneIpProxy(BaseModel):
    """scene ip proxy"""
    name: str
    ip: str
    protocol: str
    port: int


class SceneProxyUpdate(BaseModel):
    """Scene update"""
    proxy: str
    name: str

    @validator('proxy')
    def proxy_convert(cls, v: str):
        """将 proxy 转换类型"""
        return URL(v)
