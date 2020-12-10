# Sense Record

A cross-platform application for saving data streams from biosensor hardware using the [BrainFlow Python API](https://brainflow.readthedocs.io/en/stable/UserAPI.html#python-api-reference).

Sense Record is designed for a research lab setting, where the user (experimenter, study staff) needs to ensure that the raw file stream is being saved and that the file is saved along with information about the experimental session/task/run/participant.

Sense Record saves biosensor recordings using file naming conventions compliant with the [Brain Imaging Data Structure (BIDS)](https://bids-specification.readthedocs.io/en/stable/). The user is prompted to enter the subject/participant, session, task, and run information before starting any recording. This data is then used by Sense Record to generate the output file name and sub directory names, along with BIDS-spec metadata files that it saves with each recording.

## Installation

Invoke `pip` as appropriate in your environment to do:

```bash
pip install senserecord
```

## Usage

Sense Record provides three types of interfaces for recording biosensor data with BrainFlow: a GUI desktop app, a command-line interface, and a REST web services API.

To launch the GUI desktop app:  
`senserecord-gui`

To launch the CLI console app:  
`senserecord`

To launch the local http server and web app with REST API:  
`senserecord-http`

Learn more about each of these interfaces in the sections below.

### GUI Desktop Application

The GUI provides controls for starting and stopping recordings. It prompts you for run information (BIDS fields) at the start of each recording run.

![Screenshot](screenshot.png)

1. Launch the GUI by running the command: `senserecord-gui`
2. In the menu bar, select **File > Load configuration file** and load your `.yml` file. Use the example configuration files in [`/examples`](examples) to create your config file.
3. Press the "Start Recording" button. A dialog will appear, prompting you to enter information (BIDS fields) about your recording.
4. Record until your task/run is finished.
5. Press the "Stop Recording" button.
6. Find your recording's raw data file in `[bidsroot]/sourcedata/sub-[subject]/ses-[session]/[data_type]/*.csv`

### CLI Application

Sense Record comes with an interactive command-line interface.

Type `senserecord` with no arguments and it shows you help text.

Type `senserecord start` with no arguments and you are prompted for input, like this:

```bash
Enter your board name: SYNTHETIC_BOARD
Enter the path to the root directory of your project: ./
Subject name/ID: 001
Session name: testSession
Task name: myExperiment
Run number: 001
Data type. Choices: eeg, ecg,: eeg
Now recording from SYNTHETIC_BOARD
Stop the recording? [y/N]: n
Stop the recording? [y/N]: y
Stopped recording from SYNTHETIC_BOARD
```

This example run created a test directory `sourcedata/sub-001/ses-testSession/eeg` with a data file inside named `sub-001_ses-testSession_task-myExperiment_run-001_eeg.csv`.

You can also bypass the prompts with command-line arguments, like this example:

```bash
:$ senserecord start --board-name SYNTHETIC_BOARD --serial-port /dev/ttyUSB0 --bidsroot /home/myuser/my_experiment_dir --sub 001 --ses mySession --task myTask --run 001 --data-type eeg
```

Type `senserecord start --help` to see available options.

### REST Web Services API

You can control recordings over http using the built-in REST web services API. Start the REST server with:

```bash
senserecord-http
```

This will launch the server process and try to open the http endpoint in your browser at [http://127.0.0.1:8000](http://127.0.0.1:8000). Visit that URL and you get interactive HTML documentation that allows you to start and stop recordings from your browser. You can also use it to build URLs like the one used in the example below.

### Example usage of the REST API

Recordings can be started with a GET request, with parameters in the query string of the URL.

Visit this example URL and it will start recording from `SYNTHETIC_BOARD`:

```
http://127.0.0.1:8000/start/SYNTHETIC_BOARD?bidsroot=%2Fhome%2Flink%2FDownloads&serial_port=%2Fdev%2FttyUSB0&sub=001&ses=default&task=default&run=001&data_type=eeg&modality=eeg
```

It returns a simple JSON response that looks something like this:

```json
{
  "status": "ok",
  "result": {
    "board": {
      "name": "SYNTHETIC_BOARD",
      "is_ready": false,
      "is_recording": true
    }
  },
  "details": []
```

Don't forget to stop the recording! You can do that by visiting this URL:

```
http://127.0.0.1:8000/stop/SYNTHETIC_BOARD
```

When the recording stops, the API returns this JSON response smth like:

```json
{
  "status": "ok",
  "result": {
    "board": {
      "name": "SYNTHETIC_BOARD",
      "is_ready": true,
      "is_recording": false
    }
  },
  "details": []
}
```

## License

GPL-3.0-or-later

## Contact

Link Swanson (link@swanson.link)
