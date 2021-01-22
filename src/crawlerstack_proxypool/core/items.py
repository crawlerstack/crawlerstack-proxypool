"""Items"""
from datetime import datetime

from scrapy import Field, Item


class ProxyUrlItem(Item):  # pylint: disable=too-many-ancestors
    """Proxy url item"""
    url: str = Field()


class SceneItem(Item):  # pylint: disable=too-many-ancestors
    """Scene item"""
    url: str = Field()
    scene: str = Field()
    speed: int = Field()
    time: datetime = Field()
    score: int = Field()
