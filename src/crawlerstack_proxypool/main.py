import click

from crawlerstack_proxypool import __version__


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('-V', '--version', is_flag=True, help='Show version and exit.')
def main(ctx, version):
    if version:
        click.echo(f'Proxypool version: {__version__}')
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


if __name__ == '__main__':
    main()  # pragma: no cover
