import pathlib
from typing import Optional
from fastapi import FastAPI, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from senserecord.core import BoardRecorder, valid_boardname

# fmt: off
class ResultJson:
    """Base class for building json response payloads."""

    def __init__(self, board: str):
        # default json result served in response:
        self.body = {
            "status": "ok",
            "result": {
                "board": {
                    "name": board
                    }
                },
            "details": [],
        }
# fmt: on

app = FastAPI(
    title="Sense Record",
    description="REST API for recording data from biosensor hardware.",
    version="0.1.0",
    docs_url=None,  # uses local static assets
    redoc_url=None,  # uses local static assets
)


# We register active recorders in a dict to keep track of them:
recorders = {}


@app.get("/")
def home():
    return RedirectResponse("/docs")


@app.get("/status/{board}")
def boardstatus(response: Response, board: str, board_params: Optional[str] = None):
    """Returns the current status of a given board name"""
    result = ResultJson(board)
    if not valid_boardname(board):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board} is unknown")
        response.status_code = 422
        return result.body
    if board in recorders:
        recorders[board].ping()
        result.body["result"]["board"]["is_ready"] = recorders[board].is_ready
        result.body["result"]["board"]["is_recording"] = recorders[board].is_recording
    else:
        # No active recorders found, so see if we can create one,
        # ping it, get its status, then delete it:
        recorder = BoardRecorder(board, board_params)
        recorder.ping()
        result.body["result"]["board"]["is_ready"] = recorder.is_ready
        result.body["result"]["board"]["is_recording"] = recorder.is_recording
        del recorder
    return result.body


@app.get("/start/{board}")
def start(
    board: str,
    bidsroot: str,
    sub: str,
    ses: str,
    task: str,
    run: str,
    board_params: Optional[dict] = {},
    data_type: Optional[str] = None,
    modality: Optional[str] = None,
    acq: Optional[str] = None,
    metadata: Optional[dict] = {},
):
    """Starts a data stream from given board to a csv file. Streaming continues until stop() is called."""

    result = ResultJson(board)
    if not valid_boardname(board):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board} is unknown")
        return result.body
    if board not in recorders:
        recorder = BoardRecorder(board, board_params)
        recorders[board] = recorder
    else:
        recorder = recorders[board]
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
    except Exception as e:
        result.body["status"] = "error"
        result.body["details"].append(str(e))
    recorder.ping()
    result.body["result"]["board"]["is_ready"] = recorders[board].is_ready
    result.body["result"]["board"]["is_recording"] = recorders[board].is_recording
    return result.body


@app.get("/stop/{board}")
def stop(board: str):
    """Stops data stream from given board and triggers writing post-recording files."""

    result = ResultJson(board)
    if not valid_boardname(board):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board} is unknown")
        return result.body
    if board in recorders:
        if recorders[board].is_recording:
            try:
                # Stop the file stream:
                recorders[board].stop()
                result.body["result"]["board"]["is_ready"] = recorders[board].is_ready
                result.body["result"]["board"]["is_recording"] = recorders[
                    board
                ].is_recording
                # Remove the recorder object from the recorders dict:
                recorder = recorders.pop(board)
                # Delete the recorder object
                del recorder
            except Exception as e:
                result.body["status"] = "error"
                result.body["details"].append(str(e))
                result.body["result"]["board"]["is_recording"] = recorders[
                    board
                ].is_recording
        else:
            result.body["details"].append(f"{board} had no active sessions to stop.")
            result.body["result"]["board"]["is_recording"] = False
    else:
        result.body["details"].append(f"{board} had no active sessions to stop.")
        result.body["result"]["board"]["is_recording"] = False
    return result.body


# Configuration of auto-docs with static assets,
# so that they work without Internet connection:
app.mount(
    "/static",
    StaticFiles(directory=pathlib.Path(__file__).parent.absolute().joinpath("static")),
    name="static",
)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - REST UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )
