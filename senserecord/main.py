"""
Sense Record

Sense Record is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Sense Record is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sense Record.  If not, see <https://www.gnu.org/licenses/>.
"""

__author__ = "Link Swanson"
__copyright__ = "Copyright (C) 2020 Link Swanson"
__license__ = "GPL-3.0-or-later"

import sys
import typer
from PyQt5.QtWidgets import QApplication
import uvicorn
from senserecord.cli import cli
from senserecord.gui import MainWindow
from senserecord.http import app as web


def console():
    """Runs the CLI app."""
    cli()


def gui():
    """Runs the GUI app."""

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


def http():
    """
    Runs the REST API http endpoint on localhost.
    """
    # See:
    # https://www.uvicorn.org/deployment/
    # https://fastapi.tiangolo.com/#example
    # https://typer.tiangolo.com/tutorial/launch/

    typer.echo("Launching web browser to api docs:")
    typer.launch("http://127.0.0.1:8000/docs")

    uvicorn.run(
        "senserecord.main:web",
        host="127.0.0.1",
        port=8000,
        reload=True,  # For development
        log_level="info",
    )
