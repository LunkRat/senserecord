import typer
import os
from pyshortcuts import make_shortcut

cli = typer.Typer()


@cli.callback()
def callback():
    """
    Sense Record CLI
    """


@cli.command()
def start():
    """
    Start the recording.
    """
    typer.echo("Starting recording ...")


@cli.command()
def stop():
    """
    Stop the recording.
    """
    typer.echo("Stopping recording ...")

