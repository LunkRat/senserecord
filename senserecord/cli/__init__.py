import os
import json
from typing import Optional
import typer
from senserecord.core import BoardRecord, valid_boardname
from senserecord.restapi import ResultJson

cli = typer.Typer()


@cli.callback()
def callback():
    """
    Sense Record CLI
    Record data streams from biosensor hardware.
    """


@cli.command()
def status(board: str):
    """Returns the current status of a given board name."""
    board_params = {}
    if not valid_boardname(board):
        typer.secho(f"Boardname {board} is unknown", fg=typer.colors.RED)
    # create a recorder, ping it, get its status, then delete it:
    recorder = BoardRecord(board, board_params)
    recorder.ping()
    if recorder.is_ready and not recorder.is_recording:
        typer.secho(f"{board} is ready", fg=typer.colors.GREEN)
    del recorder


@cli.command()
def start(
    board: str = typer.Option(..., prompt="Enter your board name"),
    bidsroot: str = typer.Option(
        ..., prompt="Enter the path to the root directory of your project"
    ),
    sub: str = typer.Option(..., prompt="Subject name/ID"),
    ses: str = typer.Option(..., prompt="Session name"),
    task: str = typer.Option(..., prompt="Task name"),
    run: str = typer.Option(..., prompt="Run number"),
    data_type: Optional[str] = None,
    modality: Optional[str] = None,
    acq: Optional[str] = None,
):
    """
    Starts a data stream from given board to a csv file.
    Streaming continues until the user stops it via an interactive CLI prompt.
    """
    # No architecture for accepting params or metadata,
    # so pass empty dicts for now as placeholders:
    metadata = {"task": {"board": {}}}
    board_params = {}
    if not valid_boardname(board):
        typer.secho(f"Boardname {board} is unknown", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    recorder = BoardRecord(board, board_params)
    user_input = {
        "task": task,
        "run": run,
        "sub": sub,
        "ses": ses,
    }
    if bool(data_type):
        user_input["type"] = data_type
    if bool(acq):
        user_input["acq"] = acq
    if bool(modality):
        user_input["modality"] = modality
    try:
        recorder.start(bidsroot, user_input, metadata)
        recorder.ping()
        if recorder.is_recording:
            typer.secho(f"Now recording from {board}", fg=typer.colors.GREEN)
            while True:
                finished = typer.confirm("Stop the recording?")
                if finished:
                    try:
                        recorder.stop()
                        typer.secho(
                            f"Stopped recording from {recorder.board_name}",
                            fg=typer.colors.GREEN,
                        )
                        break
                    except Exception as e:
                        typer.secho(
                            f"Failed to stop recording from {recorder.board_name} \n"
                            + str(e),
                            fg=typer.colors.RED,
                        )

    except Exception as e:
        typer.secho(
            f"Failed to start recording from {board} \n" + str(e), fg=typer.colors.RED
        )
