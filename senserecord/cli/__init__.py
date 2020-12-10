import os
import json
from typing import Optional
import typer
from senserecord.core import BoardRecord, valid_boardname

cli = typer.Typer()


@cli.callback()
def callback():
    """
    Sense Record CLI\n
    Record data streams from biosensor hardware.
    """


@cli.command()
def status(
    board_name: str,
    serial_port: Optional[str] = "",
    mac_address: Optional[str] = "",
    ip_address: Optional[str] = "",
    ip_port: Optional[int] = 0,
    ip_protocol: Optional[int] = 0,
    other_info: Optional[str] = "",
    timeout: Optional[int] = 0,
    serial_number: Optional[str] = "",
    board_file: Optional[str] = "",
):
    """Returns the current status of a given board name."""
    if not valid_boardname(board_name):
        typer.secho(f"Boardname {board_name} is unknown", fg=typer.colors.RED)
    else:
        try:
            recorder = BoardRecord(
                board_name=board_name,
                serial_port=serial_port,
                mac_address=mac_address,
                ip_address=ip_address,
                ip_port=ip_port,
                ip_protocol=ip_protocol,
                other_info=other_info,
                timeout=timeout,
                serial_number=serial_number,
                board_file=board_file,
            )
        except Exception as e:
            typer.secho(
                f"Failed to check status of {board_name} \n" + str(e),
                fg=typer.colors.RED,
            )
        recorder.ping()
        if recorder.is_ready and not recorder.is_recording:
            typer.secho(f"{board_name} is ready", fg=typer.colors.GREEN)
        del recorder


@cli.command()
def start(
    board_name: str = typer.Option(..., prompt="Enter your board name"),
    bidsroot: str = typer.Option(
        ..., prompt="Enter the path to the root directory of your project"
    ),
    sub: str = typer.Option(..., prompt="Subject name/ID"),
    ses: str = typer.Option(..., prompt="Session name"),
    task: str = typer.Option(..., prompt="Task name"),
    run: str = typer.Option(..., prompt="Run number"),
    data_type: str = typer.Option(..., prompt="Data type. Choices: eeg, emg, ecg, eog"),
    serial_port: Optional[str] = "",
    mac_address: Optional[str] = "",
    ip_address: Optional[str] = "",
    ip_port: Optional[int] = 0,
    ip_protocol: Optional[int] = 0,
    other_info: Optional[str] = "",
    timeout: Optional[int] = 0,
    serial_number: Optional[str] = "",
    board_file: Optional[str] = "",
    modality: Optional[str] = None,
    acq: Optional[str] = None,
):
    """
    Starts a data stream from given board to a csv file.
    Streaming continues until the user stops it via an interactive CLI prompt.
    """
    # No architecture for accepting params or metadata,
    # so pass empty dicts for now as placeholders:
    if not valid_boardname(board_name):
        typer.secho(f"Boardname {board_name} is unknown", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    try:
        recorder = BoardRecord(
            board_name=board_name,
            serial_port=serial_port,
            mac_address=mac_address,
            ip_address=ip_address,
            ip_port=ip_port,
            ip_protocol=ip_protocol,
            other_info=other_info,
            timeout=timeout,
            serial_number=serial_number,
            board_file=board_file,
        )
        recorder.start(
            bidsroot=bidsroot,
            sub=sub,
            ses=ses,
            task=task,
            run=run,
            data_type=data_type,
            modality=modality,
            acq=acq,
        )
        recorder.ping()
        if recorder.is_recording:
            typer.secho(f"Now recording from {board_name}", fg=typer.colors.GREEN)
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
            f"Failed to start recording from {board_name} \n" + str(e),
            fg=typer.colors.RED,
        )
