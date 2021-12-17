from contextlib import contextmanager
from pathlib import Path

import click

from .tesliper import Tesliper, __version__
from .writing.serializer import ArchiveWriter


@contextmanager
def get_tesliper(session: Path, mode: str):
    create = not session.exists()
    tslr = Tesliper() if create else Tesliper.load(session)
    with ArchiveWriter(session, mode) as archive:
        if create:
            archive.write(tslr)
        yield {"tslr": tslr, "arch": archive}


# TODO: add confirmation?
def delete_session(ctx, value, param):
    if not value or ctx.resilient_parsing:
        return
    session: Path = ctx.params["session"]
    if session.exists():
        session.unlink()
    ctx.exit()


@click.group(chain=True)
@click.option(
    "-s", "--session", type=Path, show_default=True, default=".tslr", is_eager=True
)
@click.option("-O", "--overwrite/--no-overwrite", default=False)
@click.option(
    "-D", "--delete", is_flag=True, callback=delete_session, expose_value=False
)
@click.version_option(__version__)
@click.pass_context
def cli(ctx, session: Path, overwrite: bool):
    no_overwrite_mode = "a" if session.exists() else "x"
    ctx.obj = ctx.with_resource(
        get_tesliper(session, mode="w" if overwrite else no_overwrite_mode)
    )


@cli.command()
@click.pass_obj
def debug(obj):
    click.echo(obj)
