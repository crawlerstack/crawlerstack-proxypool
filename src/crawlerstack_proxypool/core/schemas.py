"""Data schema"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class BaseTaskSchema(BaseModel):  # pylint: disable=too-few-public-methods
    """
    customs_settings:   自定义 settings 在创建 crawler 的时候整合
                        注意，一定要严格按照 Scrapy 配置格式
    interval：   任务运行时间间隔，会被 DEFAULT_TIME_WINDOW 参数影响
    """
    name: str
    enable: bool
    interval: int
    customs_settings: Optional[Dict[str, Any]] = {}


class SceneTaskSchema(BaseTaskSchema):  # pylint: disable=too-few-public-methods
    """
    加载场景数据的任务配置
    upstream: 为当前场景依赖的上游队列
        比如对于一个要抓取 baidu 的网站，就需要 https 代理。所以在初始化这个场景的时候，
        会先从 https 队列中加载代理到 proxypool:baidu:seed 队列中。场景爬虫会使用该
        队列中的代理去访问 `https://www.bakdu.com` 网站，如果可以使用就放到该场景的
        评级队列中。
        如果 upstream 为空，抓取到的爬虫会直接将初始代理写入队列。
    verify_urls: 场景校验时请求的 URL。
    verify_urls_from_redis： 从 redis 中获取场景校验所需要的 URL 。如果启动，则从 Redis
        中获取，默认使用 verify_urls 中的 URL 。
    checker_name:   The name of checker you want to use
    checker_rule:   Checker rule

    """
    upstream: List[str]
    checker_name: str
    checker_rule: Optional[Dict[str, Any]] = {}
    verify_urls: List[str]
    verify_urls_from_redis: Optional[bool] = False


class PageTaskSchema(BaseTaskSchema):  # pylint: disable=too-few-public-methods
    """
    爬虫任务配置
    """
    task_type: str
    resource: Union[List[str], str]
    parser_name: str
    parser_rule: Dict[str, Any]


class SceneModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Scene model"""
    name: str
    url: str
    score: Optional[int] = 5
    time: bool
    speed: int


class ProxyIpModel(BaseModel):  # pylint: disable=too-few-public-methods
    """Proxy ip model"""
    name: str
    url: str
    score: str
    time: str
    speed: str
