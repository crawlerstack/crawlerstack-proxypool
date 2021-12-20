import logging

import pytest

from dependency_injector.wiring import inject, Provide

from crawlerstack_proxypool.container import Container, scoping_session

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s')

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_scoping_session(container):
    logger.debug('Start test...')

    @scoping_session()
    @inject
    async def foo(db=Provide[Container.db]):
        """"""
        logger.debug('Start foo...')

    await foo()
    logger.debug('Stop test...')
