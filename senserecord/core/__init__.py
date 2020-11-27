import os.path
import logging
import json
import yaml
from typing import Dict
from pathlib import Path
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

# Log settings:
BoardShim.disable_board_logger()


class BoardRecord(object):
    """
    Provides methods for communicating with a board
    and saving data in BIDS-compliant files.
    """

    def __init__(
        self,
        board_name: str,
        serial_port: str = "",
        mac_address: str = "",
        ip_address: str = "",
        ip_port: int = 0,
        ip_protocol: int = 0,
        other_info: str = "",
        timeout: int = 0,
        serial_number: str = "",
        board_file: str = "",
    ):

        self.board_name = board_name
        if not valid_boardname(board_name):
            raise BoardException(f"Invalid board name in config: {self.board_name}")
        else:
            self.board_id = BoardIds[self.board_name].value
        # Get and set vars with basic info about the board:
        self.sample_rate = BoardShim.get_sampling_rate(self.board_id)
        self.channel_names = BoardShim.get_eeg_names(self.board_id)
        self.channel_count = len(BoardShim.get_eeg_channels(self.board_id))
        # Prepare the board params object:
        self.params = BrainFlowInputParams()
        # Load params into the object from init function args:
        self.params.serial_port = serial_port
        self.params.mac_address = mac_address
        self.params.ip_address = ip_address
        self.params.ip_port = ip_port
        self.params.ip_protocol = ip_protocol
        self.params.other_info = other_info
        self.params.timeout = timeout
        self.params.serial_number = serial_number
        self.params.file = board_file

        # Construct the board object:
        try:
            self.board = BoardShim(self.board_id, self.params)
        except Exception as e:
            raise BoardException(
                f"Failed to instantiate board object for {self.board_name}" + str(e)
            )
        # Initial values:
        self.is_ready = False
        self.is_recording = False
        # Self-check via our 'ping' function:
        self.ping()

    def ping(self) -> bool:
        """Test to see if the board responds to prepare_session method call."""
        if self.is_recording:
            self.is_ready = False
        else:
            try:
                self.board.prepare_session()
                self.board.release_session()
                self.is_ready = True
                return True
            except Exception:  # @todo be more granular about handling exceptions.
                self.is_ready = False
                return False

    def start(
        self,
        bidsroot: str,
        sub: str = "",
        ses: str = "",
        task: str = "",
        run: str = "",
        data_type: str = "",
        modality: str = "",
        acq: str = "",
    ):
        """Start data stream from board and save to output file"""
        self.bidsroot = bidsroot
        # Raise an exception if the BIDS base path does not exist:
        if not os.path.exists(self.bidsroot):
            raise FileSystemException(
                f"Non-existent base directory path specified in config. Check config or create the directory: {self.bidsroot}"
            )
        self.sub = sub
        self.ses = ses
        self.task = task
        self.run = run
        self.data_type = data_type
        self.modality = modality
        self.acq = acq
        # Set make file paths and set variables:
        self.set_file_paths()
        # Start streaming data from the board, save data to an output file:
        try:
            self.board.prepare_session()
            self.board.start_stream(45000, self.file_param)
            self.is_recording = True
            self.is_ready = False
        except Exception as e:
            raise BoardException(str(e))

    def stop(self):
        """Stops recording, releases session with board, and saves sidecar json file."""

        try:
            self.board.stop_stream()
            self.board.release_session()
            self.is_recording = False
            self.ping()
        except Exception as e:
            raise BoardException(str(e))
        # Write the sidecar json file:
        # DISABLED FOR DEVELOPMENT OF CLI:
        # self.write_sidecar()

    def release(self):
        """Releases session with board."""

        try:
            self.board.release_session()
            self.is_recording = False
            self.is_ready = True
        except Exception as e:
            raise BoardException(str(e))

    def set_file_paths(self):
        """Generates file paths and sets file path variables for recording."""
        # ref: https://bids-specification.readthedocs.io/en/stable/02-common-principles.html
        if not bool(self.data_type):
            # No type was given,
            # so provide a sensible default:
            if bool(self.modality):
                self.data_type = self.modality
            else:
                self.data_type = "DATA-TYPE-UNKNOWN"
        if not bool(self.modality):
            # No modality was given in config or user input,
            # so provide a sensible default:
            if bool(self.data_type):
                self.modality = self.data_type
            else:
                self.modality = "MODALITY-UNKNOWN"
        # Construct the path to the recording output directory:
        self.data_path = os.path.join(
            self.bidsroot,
            # we are recording raw csv,
            # so we output to ./sourcedata
            "sourcedata",
            "sub-" + self.sub,
            "ses-" + self.ses,
            self.data_type,
            "",  # trailing slash
        )
        # Ensure the recording output directory exists:
        Path(self.data_path).mkdir(parents=True, exist_ok=True)
        # Construct the name of the recording output file
        # formatted to BIDS standard
        # (ref: https://bids-specification.readthedocs.io/en/stable/02-common-principles.html):
        self.data_file_base = (
            "sub-"
            + self.sub
            + "_ses-"
            + self.ses
            + "_task-"
            + self.task
            + "_run-"
            + self.run
            + "_"
            + self.modality
        )
        # Ensure that the file does not already exist:
        if os.path.exists(self.data_path + self.data_file_base + ".csv"):
            raise FileSystemException(
                f"A file already exists at {self.data_path + self.data_file_base + '.csv'}.\n\nYou must either delete the file from its current location, or enter different information when starting the recording."
            )
        self.file_param = (
            "file://" + self.data_path + self.data_file_base + ".csv" + ":w"
        )

    def write_sidecar(self):
        """Generates metadata and writes it to a BIDS json sidecar file."""
        data = {
            "SamplingFrequency": self.sample_rate,
            "EEGChannelCount": self.channel_count,
            # "TriggerChannelCount":1,
            # "RecordingDuration":600,
            # "RecordingType":"continuous"
        }
        if "label" in self.metadata["task"]:
            data["TaskName"] = self.metadata["task"]["label"]
        if "description" in self.metadata["task"]:
            data["TaskDescription"] = self.metadata["task"]["description"]
        if "instructions" in self.metadata["task"]:
            data["Instructions"] = self.metadata["task"]["instructions"]
        if "institution" in self.metadata["task"]:
            data["InstitutionName"] = self.metadata["task"]["institution"]
        if "manufacturer" in self.metadata["board"]:
            data["Manufacturer"] = self.metadata["board"]["manufacturer"]
        if "modelname" in self.metadata["board"]:
            data["ManufacturersModelName"] = self.metadata["board"]["modelname"]
        if "cap" in self.metadata["board"]:
            if "manufacturer" in self.metadata["board"]["cap"]:
                data["CapManufacturer"] = self.metadata["board"]["cap"]["manufacturer"]
            if "modelname" in self.metadata["board"]["cap"]:
                data["CapManufacturersModelName"] = self.metadata["board"]["cap"][
                    "modelname"
                ]
        try:
            with open((self.data_file_base + ".json"), "w") as outfile:
                json.dump(data, outfile, indent=4, sort_keys=True)
            logging.info(
                f"Sidecar json file written to {self.data_file_base + '.json'}"
            )
        except Exception:
            raise FileSystemException(
                f"Failed to create sidecar json file {self.data_file_base + '.json'}"
            )


class BoardException(Exception):
    def __init__(self, msg: str) -> str:
        self.msg = msg

    def __str__(self):
        return self.msg


class FileSystemException(Exception):
    def __init__(self, msg: str) -> str:
        self.msg = msg

    def __str__(self):
        return self.msg


class ConfigFileException(Exception):
    def __init__(self, msg: str) -> str:
        self.msg = msg

    def __str__(self):
        return self.msg


def valid_boardname(boardname: str):
    if boardname in BoardIds.__members__:
        return True
    else:
        return False


def process_yaml(path: str) -> dict:
    """Loads YAML from yml file and checks it for required keys."""
    try:
        try:
            # Open the file and load into dict 'data'
            data = yaml.load(open(path), Loader=yaml.FullLoader)
        except Exception as e:
            raise ConfigFileException(str(e))
        # Audit the file for some required keys:
        if "tasks" in data:
            for task, values in data["tasks"].items():
                if "bidsroot" not in values:
                    raise ConfigFileException(
                        f"Required key 'bidsroot' is missing from {task} section of config file {path}"
                    )
                if "boards" in values:
                    for board, settings in values["boards"].items():
                        if "board_name" not in settings:
                            raise ConfigFileException(
                                f"Required key 'board_name' is missing from {board} section of {task} in config file {path}"
                            )
                        if not valid_boardname(settings["board_name"]):
                            raise ConfigFileException(
                                f"Invalid name '{settings['board_name']}' in {board} section of {task} in config file {path}"
                            )
        else:
            raise ConfigFileException(
                f"Required root key 'tasks' is missing from the config file {path}"
            )
        # Got past all exceptions so return the dict:
        return data
    except Exception as e:
        raise ConfigFileException(str(e))
