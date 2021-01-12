"""Test package"""
import os

from crawlerstack_proxypool.config import settings

settings.load_file(os.path.join(os.path.dirname(__file__), 'settings.local.yml'))
