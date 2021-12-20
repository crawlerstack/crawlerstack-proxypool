"""Test config"""
import pytest
from click.testing import CliRunner

from crawlerstack_proxypool import config
from crawlerstack_proxypool.application import Application
from crawlerstack_proxypool.container import Container


@pytest.fixture()
def cli_runner():
    runner = CliRunner()
    yield runner


@pytest.fixture()
def settings():
    yield config.settings


@pytest.fixture()
def application():
    yield Application()


@pytest.fixture()
def container(application):
    yield application.container


@pytest.fixture()
async def session():
    """"""
    # Database()
