import logging
from logging.config import dictConfig

from crawlerstack_proxypool.config import settings

DEFAULT_FORMATTER = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def verbose_formatter(verbose: bool) -> str:
    if verbose is True:
        return 'verbose'
    else:
        return 'simple'


def log_level(debug: bool, level: str) -> str:
    if debug is True:
        level_num = logging.DEBUG
    else:
        level_num = logging.getLevelName(level)
    settings.set('LOGLEVEL', logging.getLevelName(level_num))
    return settings.LOGLEVEL


def init_logging_config():
    level = log_level(settings.DEBUG, settings.LOGLEVEL)

    # os.makedirs(settings.LOGPATH, exist_ok=True)

    default_logging = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            'verbose': {
                'format': '%(asctime)s %(levelname)s %(name)s %(process)d %(thread)d %(message)s'
            },
            'simple': {
                'format': '%(asctime)s %(levelname)s %(message)s'
            },
        },
        "handlers": {
            "console": {
                "formatter": verbose_formatter(settings.VERBOSE),
                'level': 'DEBUG',
                "class": "logging.StreamHandler",
            },
            # 'file': {
            #     'class': 'logging.handlers.RotatingFileHandler',
            #     'level': 'DEBUG',
            #     'formatter': verbose_formatter(settings.VERBOSE),
            #     'filename': os.path.join(settings.LOGPATH, 'all.log'),
            #     'maxBytes': 1024 * 1024 * 1024 * 200,  # 200M
            #     'backupCount': '5',
            #     'encoding': 'utf-8'
            # },
            # 'access_file': {
            #     'class': 'logging.handlers.RotatingFileHandler',
            #     'level': 'DEBUG',
            #     'formatter': 'access',
            #     'filename': os.path.join(settings.LOGPATH, 'access.log'),
            #     'maxBytes': 1024 * 1024 * 1024 * 200,  # 200M
            #     'backupCount': '5',
            #     'encoding': 'utf-8'
            # }
        },
        "loggers": {
            '': {'level': level, 'handlers': ['console']},
        }
    }
    return default_logging


def configure_logging():
    dictConfig(init_logging_config())
