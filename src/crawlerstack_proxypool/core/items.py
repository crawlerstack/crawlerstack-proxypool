"""Items"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProxyUrlItem:
    """Proxy url item"""
    url: str


@dataclass
class SceneItem:
    """Scene item"""
    url: str
    scene: str
    speed: int
    time: datetime
    score: int
