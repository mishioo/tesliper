import click
from tesliper import Tesliper, ArchiveWriter
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def get_tesliper(session: Path, mode: str):
    t = Tesliper() if not session.exists() else Tesliper.load(session)
    with ArchiveWriter(session, mode) as archive:
        yield {"tslr": t, "arch": archive}


@click.group()
@click.option("-s", "--session", type=Path, show_default=True, default=".tslr")
@click.option("-O", "--overwrite/--no-overwrite", default=False)
@click.pass_context
def tesliper(ctx, session: Path, overwrite: bool):
    no_overwrite_mode = "a" if session.exists() else "x"
    ctx.obj = ctx.with_resource(
        get_tesliper(session, mode="w" if overwrite else no_overwrite_mode)
    )
