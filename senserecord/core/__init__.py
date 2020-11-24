import os.path
import logging
import json
import yaml
from pathlib import Path
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds


class BoardRecorder:
    """
    Provides methods for communicating with a board
    and saving data in BIDS-compliant files.
    """

    def __init__(self, board_name: str, board_params: dict = {}):

        # Construct board using the BrainFlow API:
        self.board_name = board_name
        if not valid_boardname(board_name):
            raise BoardException(f"Invalid board name in config: {self.board_name}")
        else:
            self.board_id = BoardIds[self.board_name].value
        # Get and set vars with basic info about the board:
        self.sample_rate = BoardShim.get_sampling_rate(self.board_id)
        self.channel_names = BoardShim.get_eeg_names(self.board_id)
        self.channel_count = len(BoardShim.get_eeg_channels(self.board_id))
        # Prepare the board params:
        self.params = BrainFlowInputParams()
        # Pass all board params from argument dict
        # into the BrainFlowInputParams object:
        for name, value in board_params.items():
            setattr(self.params, name, value)
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

    def start(self, bidsroot: str, user_input: dict, metadata: dict = {}):
        """Start data stream from board and save to output file"""
        self.bidsroot = bidsroot
        # Raise an exception if the BIDS base path does not exist:
        if not os.path.exists(self.bidsroot):
            raise FileSystemException(
                f"Non-existent base directory path specified in config. Check config or create the directory: {self.bidsroot}"
            )
        self.user_input = user_input
        self.metadata = metadata
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
        self.write_sidecar()

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
        if "type" not in self.user_input:
            # No type was given in config or user input,
            # so provide a sensible default:
            if "modality" in self.user_input:
                self.user_input["type"] = self.user_input["modality"]
            else:
                self.user_input["type"] = "DATA-TYPE-UNKNOWN"
        if "modality" not in self.user_input:
            # No modality was given in config or user input,
            # so provide a sensible default:
            if "type" in self.user_input:
                self.user_input["modality"] = self.user_input["type"]
            else:
                self.user_input["modality"] = "MODALITY-UNKNOWN"
        # Construct the path to the recording output directory:
        self.data_path = os.path.join(
            self.bidsroot,
            # we are recording raw csv,
            # so we output to ./sourcedata
            "sourcedata",
            "sub-" + self.user_input["sub"],
            "ses-" + self.user_input["ses"],
            self.user_input["type"],
            "",  # trailing slash
        )
        # Ensure the recording output directory exists:
        Path(self.data_path).mkdir(parents=True, exist_ok=True)
        # Construct the name of the recording output file
        # formatted to BIDS standard
        # (ref: https://bids-specification.readthedocs.io/en/stable/02-common-principles.html):
        self.data_file = (
            "sub-"
            + self.user_input["sub"]
            + "_ses-"
            + self.user_input["ses"]
            + "_task-"
            + self.user_input["task"]
            + "_run-"
            + self.user_input["run"]
            + "_"
            + self.user_input["modality"]
            + ".csv"
        )
        # Ensure that the file does not already exist:
        if os.path.exists(self.data_path + self.data_file):
            raise FileSystemException(
                f"A file already exists at {self.data_path + self.data_file}.\n\nYou must either delete the file from its current location, or enter different information when starting the recording."
            )
        self.file_param = "file://" + self.data_path + self.data_file + ":w"

    def write_sidecar(self):
        """Generates metadata and writes it to a BIDS json sidecar file."""
        self.sidecar_file = (
            self.data_path
            + "sub-"
            + self.user_input["sub"]
            + "_ses-"
            + self.user_input["ses"]
            + "_task-"
            + self.user_input["task"]
            + "_run-"
            + self.user_input["run"]
            + "_"
            + self.user_input["modality"]
            + ".json"
        )
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
            with open(self.sidecar_file, "w") as outfile:
                json.dump(data, outfile, indent=4, sort_keys=True)
            logging.info(f"Sidecar json file written to {self.sidecar_file}")
        except Exception:
            raise FileSystemException(
                f"Failed to create sidecar json file {self.sidecar_file}"
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
        data = yaml.load(open(path), Loader=yaml.FullLoader)
        return data
    except Exception as e:
        raise ConfigFileException(str(e))
    if "tasks" in data:
        for task, values in data["tasks"].items():
            if "bidsroot" not in values:
                raise ConfigFileException(
                    f"Required key 'bidsroot' is missing from {task} section of config file {path}"
                )
            if "boards" in values:
                for board, settings in task["boards"].items():
                    if "name" not in settings:
                        raise ConfigFileException(
                            f"Required key 'name' is missing from {board} section of {task} in config file {path}"
                        )
                    elif not valid_boardname(settings["name"]):
                        raise ConfigFileException(
                            f"Boardname {settings['name']} is unknown in {board} section of {task} in config file {path}"
                        )
            else:
                raise ConfigFileException(
                    f"Required key 'boards' is missing from {task} section of config file {path}"
                )
    else:
        raise ConfigFileException(
            f"Required root key 'tasks' is missing from the config file {path}"
        )
