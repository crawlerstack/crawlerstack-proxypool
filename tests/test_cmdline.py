"""test cmdline"""
import pytest

from crawlerstack_proxypool import __version__
from crawlerstack_proxypool.main import main


@pytest.mark.parametrize(
    'args, exit_code, contained_value',
    [
        (None, 0, '--help'),
        ('--version', 0, __version__),
        ('-V', 0, __version__),
    ]
)
def test_cmdline(cli_runner, args, exit_code, contained_value):
    """test cmdline"""
    result = cli_runner.invoke(main, args=args)
    assert result.exit_code == exit_code
    assert contained_value in result.stdout
