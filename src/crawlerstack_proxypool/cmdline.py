import click

from crawlerstack_proxypool.config import settings
from crawlerstack_proxypool.server import Server


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('-V', '--version', is_flag=True, help='Show version and exit.')
@click.option('-v', '--verbose', is_flag=True, help='Get detailed output')
def main(ctx, version, verbose, __VERSION__=None):
    if version:
        click.echo(f'Proxypool version: {__VERSION__}')
    elif verbose:
        settings.set('VERBOSE', verbose)
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option('-h', '--host', default='0.0.0.0', show_default=True, help='Host IP')
@click.option('-p', '--port', default=8080, show_default=True, help='Port')
@click.option('--level', help='Log level')
def run(host, port, level):
    kwargs = {
        'LOGLEVEL': level,
        'HOST': host,
        'PORT': port,
    }
    for name, value in kwargs.items():
        if value:
            settings.set(name, value)
    Server().start()


if __name__ == '__main__':
    main()
