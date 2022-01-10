__version__ = '0.1.0'

import asyncio
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s',
    # datefmt='%Y-%m-%d %H:%M:%S'
)
