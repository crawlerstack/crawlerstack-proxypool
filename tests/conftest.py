"""Test config"""
import pytest
from click.testing import CliRunner

from crawlerstack_proxypool import config


@pytest.fixture()
def cli_runner():
    runner = CliRunner()
    yield runner


@pytest.fixture()
def settings():
    yield config.settings
