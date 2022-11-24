"""signals"""
from aio_pydispatch import Signal

start_fetch_proxy = Signal()
start_validate_proxy = Signal()

spider_opened = Signal()
spider_closed = Signal()
