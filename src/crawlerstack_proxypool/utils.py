"""
Utils.
"""
from pydantic import AnyUrl


class SingletonMeta(type):
    """
    单例元类
    """
    __instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            instance = super().__call__(*args, **kwargs)
            cls.__instances[cls] = instance
        return cls.__instances[cls]


def update_db_settings(settings, db_file: str = 'proxypool.db'):
    """
    当数据库配置为控时，更新数据库配置，使用 sqlite
    :return:
    """
    database = getattr(settings, 'DATABASE', None)

    if not database:
        local_path = settings.LOCALPATH
        db_file = local_path / db_file
        settings.DATABASE = f'sqlite+aiosqlite:///{db_file}'


ALLOW_PROXY_SCHEMA = ('http', 'https', 'socks5')
