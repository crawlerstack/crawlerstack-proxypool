import logging
import signal

from scrapy.signalmanager import SignalManager
from scrapy.utils.ossignal import install_shutdown_handlers, signal_names
from twisted.internet import defer
from twisted.internet.defer import Deferred

from crawlerstack_proxypool import api
from crawlerstack_proxypool.tasks.manager import TaskManager
from crawlerstack_proxypool.utils.log import configure_logging

logger = logging.getLogger(__name__)


class Server:

    def __init__(self):
        install_shutdown_handlers(self._signal_shutdown)
        self.signal = SignalManager(self)
        self.task = TaskManager(self)
        configure_logging()

    def _signal_shutdown(self, signum, _):
        from twisted.internet import reactor
        install_shutdown_handlers(self._signal_kill)
        sig_name = signal_names[signum]
        logger.info(f"Received {sig_name}, shutting down gracefully. Send again to force ")
        reactor.callFromThread(self._graceful_stop_reactor)

    def _signal_kill(self, signum, _):
        from twisted.internet import reactor
        install_shutdown_handlers(signal.SIG_IGN)
        sig_name = signal_names[signum]
        logger.info(f"Received {sig_name} twice, forcing unclean shutdown.")
        reactor.callFromThread(self._stop_reactor)

    def start(self):
        from twisted.internet import reactor

        self.task.start()
        api.run(self)
        reactor.run(installSignalHandlers=False)  # blocking call

    def stop(self) -> Deferred:
        return self.task.stop()

    @defer.inlineCallbacks
    def _graceful_stop_reactor(self) -> Deferred:
        """
        等待任务停止后，停止 reactor
        :return:
        """
        yield self.stop()
        self._stop_reactor()

    def _stop_reactor(self):
        from twisted.internet import reactor
        try:
            reactor.stop()
        except RuntimeError:
            pass
