"""test schedule"""
import pytest

from crawlerstack_proxypool.tasks.scheduler import Scheduler


@pytest.fixture
def scheduler():
    """scheduler"""
    yield Scheduler()


async def test_load_fetch_task(scheduler):
    """test load fetch task"""
    config = [
        {
            'name': 'foo',
            'urls': ['https://example.com'],
            'parser': {
                'name': 'json',
            },
            'dest': ['http', 'socks5'],
            'trigger': {
                'name': 'interval',
                'params': {
                    'seconds': 123
                }
            }
        }
    ]
    scheduler.load_fetch_task(config)
    added_jobs = scheduler.apscheduler.get_jobs()
    assert len(added_jobs) == 1
    assert added_jobs[0].name == 'foo'


@pytest.mark.parametrize(
    'original',
    [True, False]
)
async def test_load_validate_task(scheduler, original):
    """test load validate task"""
    config = [
        {
            'name': 'foo',
            'urls': ['https://example.com'],
            'parser': {
                'name': 'keyword',
            },
            'original': original,
            'source': 'http',
            'dest': ['http', 'https'],
            'trigger': {
                'name': 'interval',
                'params': {
                    'seconds': 123,
                }
            }
        }
    ]
    scheduler.load_validate_task(config)
    added_jobs = scheduler.apscheduler.get_jobs()
    assert len(added_jobs) == 1
    assert added_jobs[0].name == 'foo'
    if original:
        assert scheduler.validate_fetch_jobs
    else:
        assert scheduler.validate_scene_jobs
