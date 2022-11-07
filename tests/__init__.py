"""Test package"""
from pathlib import Path

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.utils import update_db_settings


def update_test_settings():
    """
    更新测试配置
    :return:
    """
    test_config_path = Path(__file__).parent
    settings.load_file(test_config_path / 'settings.yml')
    settings.load_file(test_config_path / 'settings.local.yml')
    update_db_settings(settings, 'proxypool.test.db')


# 重置测试数据库
update_test_settings()
