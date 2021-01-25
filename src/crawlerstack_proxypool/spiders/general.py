import logging

from crawlerstack_proxypool.core.base import BasePageSpider

logger = logging.getLogger(__name__)


class GeneralSpider(BasePageSpider):
    name = 'general'  # general
