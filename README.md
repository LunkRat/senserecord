# Sense Record
A cross-platform application for saving data streams from biosensor hardware using the [BrainFlow Python API](https://brainflow.readthedocs.io/en/stable/UserAPI.html#python-api-reference).

Sense Record aims to provide simple CLI, GUI, and REST API interfaces allowing the user to easily control (start/stop) a file stream on any BrainFlow-supported board. It is designed for a research lab setting, where the user (experimenter, study staff) needs to ensure that the raw file stream is being saved and that the file is saved along with information about the experimental session/task/run/participant.

Sense Record saves biosensor recordings using file naming conventions compliant with the [Brain Imaging Data Structure (BIDS)](https://bids-specification.readthedocs.io/en/stable/). The user is prompted to enter the subject/participant, session, task, and run information before starting any recording. This data is then used by Sense Record to generate the output file name and sub directory names, along with BIDS-spec metadata files that it saves with each recording.

Sense Record reads a configuration file in YAML format, in which you can define the information about your experiment, hardware settings for connecting to the board(s), and metadata to use when saving the file streams associated with your experiment. This allows the experimenter to maintain Sense Record's configuration in version-controlled text files to ensure a known configuration of Sense Record when deployed on computers for use in live experimental sessions.

## Installation

Invoke `pip` as appropriate in your environment to do:

```bash
pip install senserecord
```

## Usage

Sense Record provides three ways to interact with biosensor data: a GUI desktop app, a command-line interface, and a REST web services API.

### GUI Application

1. Use the example configuration files in `/examples` to get started.
2. Launch the GUI by running the command: `senserecord-gui`
3. Select File > Load configuration file and load your `.yml` file.
4. Press the "Start Recording" button. A dialog will appear, prompting you to enter information (BIDS fields) about your recording.
5. Record until your task/run is finished.
6. Press the "Stop Recording" button.
7. Find your recording's raw data file in `[bidsroot]/sourcedata/sub-[subject]/ses-[session]/[type]/*_[modality].csv`

### CLI Application

Forthcoming.

### REST Web Services API

Forthcoming.

## License
GPL-3.0-or-later

## Contact
Link Swanson (link@umn.edu)
