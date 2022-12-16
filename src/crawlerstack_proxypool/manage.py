"""manage"""
import asyncio
import logging
import signal as system_signal

from dynaconf.base import Settings

from crawlerstack_proxypool.db import Database
from crawlerstack_proxypool.exceptions import CrawlerStackProxyPoolError
from crawlerstack_proxypool.log import configure_logging
from crawlerstack_proxypool.rest_api import RestAPI
from crawlerstack_proxypool.tasks.scheduler import Scheduler

HANDLED_SIGNALS = (
    system_signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    system_signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)

logger = logging.getLogger(__name__)


class ProxyPool:
    """proxypool"""

    def __init__(
            self,
            settings: Settings,
    ):
        configure_logging()
        self._settings = settings

        self._db = Database(settings)

        self._rest_api = RestAPI(
            db=self._db,
            host=self.settings.HOST,
            port=self._settings.PORT,
        )

        self.should_exit = False
        self.force_exit = True
        self.scheduler = Scheduler()

    @property
    def db(self):
        """db"""
        return self._db

    @property
    def settings(self):
        """settings"""
        return self._settings

    @property
    def rest_api(self):
        """rest api"""
        return self._rest_api

    async def init(self):
        """调度任务"""
        self.rest_api.init()
        await self.rest_api.start()
        self.scheduler.load_task()
        self.install_signal_handlers()

    async def start(self):
        """Run"""
        logger.debug('Start proxypool server .')
        try:
            await self.init()
            self.scheduler.start()
            while not self.should_exit:
                # 暂时不做任何处理。
                await asyncio.sleep(0.001)
        except CrawlerStackProxyPoolError as ex:
            logger.exception(ex)
        finally:
            await self.stop()

    async def stop(self):
        """Stop spiderkeeper"""
        logger.debug('Stop proxypool server.')
        await self.rest_api.stop()
        await self.db.close()

    def install_signal_handlers(self) -> None:
        """Install system signal handlers"""
        loop = asyncio.get_event_loop()

        try:
            for sig in HANDLED_SIGNALS:
                loop.add_signal_handler(sig, self.handle_exit, sig, None)
        except NotImplementedError:  # pragma: no cover
            # Windows
            for sig in HANDLED_SIGNALS:
                system_signal.signal(sig, self.handle_exit)

    def handle_exit(self, _sig, _frame):
        """Handle exit signal."""
        if self.should_exit:
            self.force_exit = True
        else:
            self.should_exit = True
