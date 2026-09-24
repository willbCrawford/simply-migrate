import typer

from .migrate import app as migrate_app
from .release import app as release_app

cli_wrapper = typer.Typer()
cli_wrapper.add_typer(migrate_app)
cli_wrapper.add_typer(release_app)

@cli_wrapper.callback()
def callback():
    """
    Easy to use tool for managing migrations in a multi-tenant environment.
    """

