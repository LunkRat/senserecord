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
from brainflow.board_shim import IpProtocolType
from senserecord.core import BoardRecord, valid_boardname

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


# We register active recorders in a dict to keep track of them
# in between http calls:
recorders = {}


@app.get("/")
def home():
    return RedirectResponse("/docs")


@app.get("/status/{board_name}")
def boardstatus(
    response: Response,
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
    result = ResultJson(board_name)
    if not valid_boardname(board_name):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board_name} is unknown")
        response.status_code = 422
        return result.body
    if board_name in recorders:
        recorder = recorders[board_name]
        recorder.ping()
        result.body["result"]["board"]["is_ready"] = recorder.is_ready
        result.body["result"]["board"]["is_recording"] = recorder.is_recording
    else:
        # No active recorders found, so see if we can create one,
        # ping it, get its status, then delete it:
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
            recorders[board_name] = recorder
        except Exception as e:
            result.body["status"] = "error"
            result.body["details"].append(str(e))
            response.status_code = 500
            return result.body
        recorder.ping()
        result.body["result"]["board"]["is_ready"] = recorder.is_ready
        result.body["result"]["board"]["is_recording"] = recorder.is_recording
        del recorder
    return result.body


@app.get("/start/{board_name}")
def start(
    response: Response,
    board_name: str,
    bidsroot: str,
    serial_port: Optional[str] = "",
    mac_address: Optional[str] = "",
    ip_address: Optional[str] = "",
    ip_port: Optional[int] = 0,
    ip_protocol: Optional[int] = 0,
    other_info: Optional[str] = "",
    timeout: Optional[int] = 0,
    serial_number: Optional[str] = "",
    board_file: Optional[str] = "",
    # BIDS File naming parameters
    sub: Optional[str] = "",
    ses: Optional[str] = "",
    task: Optional[str] = "",
    run: Optional[str] = "",
    data_type: Optional[str] = "",
    modality: Optional[str] = "",
    acq: Optional[str] = "",
    # metadata: Optional[dict] = {},
):
    """
    Starts a data stream from given board to a csv file.
    Streaming continues until stop() is called.
    """

    result = ResultJson(board_name)
    if not valid_boardname(board_name):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board_name} is unknown")
        response.status_code = 422
        return result.body
    if board_name not in recorders:
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
            recorders[board_name] = recorder
        except Exception as e:
            result.body["status"] = "error"
            result.body["details"].append(str(e))
            response.status_code = 500
            return result.body
    else:
        recorder = recorders[board_name]
    try:
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
    except Exception as e:
        result.body["status"] = "error"
        result.body["details"].append(str(e))
        response.status_code = 500
    recorder.ping()
    result.body["result"]["board"]["is_ready"] = recorder.is_ready
    result.body["result"]["board"]["is_recording"] = recorder.is_recording
    return result.body


@app.get("/stop/{board_name}")
def stop(response: Response, board_name: str):
    """Stops data stream from given board_name and triggers writing post-recording files."""

    result = ResultJson(board_name)
    if not valid_boardname(board_name):
        result.body["status"] = "error"
        result.body["details"].append(f"Boardname {board_name} is unknown")
        response.status_code = 422
        return result.body
    if board_name in recorders:
        recorder = recorders[board_name]
        if recorder.is_recording:
            try:
                # Stop the file stream:
                recorder.stop()
                result.body["result"]["board"]["is_ready"] = recorder.is_ready
                result.body["result"]["board"]["is_recording"] = recorder.is_recording
                # Remove the recorder object from the recorders dict:
                recorder = recorders.pop(board_name)
                # Delete the recorder object
                del recorder
            except Exception as e:
                result.body["status"] = "error"
                result.body["details"].append(str(e))
                result.body["result"]["board"]["is_recording"] = recorder.is_recording
                response.status_code = 500
        else:
            result.body["details"].append(
                f"{board_name} had no active sessions to stop."
            )
            result.body["result"]["board"]["is_recording"] = False
    else:
        result.body["details"].append(f"{board_name} had no active sessions to stop.")
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
