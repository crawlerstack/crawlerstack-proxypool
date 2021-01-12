"""Init global Configuration"""
import os
import sys
from pathlib import Path

from dynaconf import Dynaconf

# https://www.dynaconf.com/

_base_dir = Path(__file__).parent.parent

_settings_files = [
    # All config file will merge.
    Path(__file__).parent.joinpath('settings.yml'),  # Load default config.
    # Load task if file exist.
    Path(__file__).parent.joinpath('tasks', 'spider_task.yml'),
    Path(__file__).parent.joinpath('tasks', 'scene_task.yml'),
]

_external_files = [
    # Why not use Path ?
    # https://github.com/rochacbruno/dynaconf/issues/494
    os.path.join(sys.prefix, 'etc', 'crawlerstack', 'proxypool', 'settings.yml')
]

settings = Dynaconf(
    # You can set `CRAWLERSTACK_PROXYPOOL_FOO=ABC`, and access by `settings.FOO`.
    envvar_prefix="CRAWLERSTACK_PROXYPOOL",
    settings_files=_settings_files,
    load_dotenv=True,
    lowercase_read=False,  # Disable lowercase， can't access name by `settings.name`.
    includes=_external_files,  # External customs config, will override `settings_files`.
    base_dir=_base_dir
)
