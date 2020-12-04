import os.path
import logging
from typing import Optional
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (
    QWidget,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QPlainTextEdit,
    QGridLayout,
    QMessageBox,
    QProgressBar,
)
import qtawesome as qta
from senserecord.core import BoardRecord

# Custom widget class for Start/Stop record buttons:
# (Thank you John Lim: https://www.learnpyqt.com/tutorials/widget-search-bar/)
class OnOffWidget(QWidget):
    def __init__(self, board: dict, task: dict):
        super(OnOffWidget, self).__init__()
        self.board = board
        if 'params' not in self.board:
            self.board['params'] = {}
        self.task = task
        self.is_on = False  # Current button state (true=ON, false=OFF)
        # Construct the record button
        self.recordButton = QPushButton(
            qta.icon("mdi.record-circle-outline", color="#fff"), "Start recording"
        )
        # supersizes the button:
        # self.recordButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.recordButton.clicked.connect(self.on)
        statusIcon = qta.IconWidget()
        statusIcon.setIconSize(QSize(42, 42))
        icon_online = qta.icon("mdi.check-network", color="#4CAF50")
        icon_offline = qta.icon("mdi.network-off")
        # Construct the recorder object with minimum values:
        try:
            self.recorder = BoardRecord(
                board_name=self.board["board_name"],
                # Pass the 'params' dict as a kwargs mapping:
                **self.board["params"]
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Failed to create recorder object: ", str(e), QMessageBox.Ok
            )
            logging.exception("Failed to create recorder object.")
            return
        # Check the board status to see if it is reachable:
        self.is_online = self.recorder.ping()
        if self.is_online:
            statusIcon.setIcon(icon_online)
            statusLabel = QLabel("Online")
        else:
            statusIcon.setIcon(icon_offline)
            statusLabel = QLabel("Offline")
            self.recordButton.setDisabled(True)
        statusLabel.setBuddy(statusIcon)
        boardInfo = BoardInfoWidget(self)
        # Place controls into layouts:
        hbox = QHBoxLayout()
        hbox.addWidget(boardInfo, 3)
        hbox.addWidget(statusIcon, 0.5)
        hbox.addWidget(statusLabel, 2.5)
        hbox.addWidget(self.recordButton, 6)
        # Construct a GroupBox to render our hbox layout:
        groupBox = QGroupBox(self.board["board_name"])
        # Set the GroupBox to render the layout and its widgets:
        groupBox.setLayout(hbox)
        vbox = QVBoxLayout()
        vbox.addWidget(groupBox)  # Place the groupBox into a vertical box
        self.setLayout(vbox)  # Set vbox/groupBox as the root layout for entire widget
        # Set initial button state
        self.update_button_state()

    def on(self):
        """
        Called when Start button is clicked.
        Initiates a session with the board and streams data to a file.
        """
        if "bidsroot" in self.task:
            self.bidsroot = self.task["bidsroot"]
        else:
            self.bidsroot = "./"
        if 'data_type' not in self.board:
            self.board['data_type'] = ''
        if 'modality' not in self.board:
            self.board['modality'] = ''
        # Prompt the user to enter BIDS fields before starting recording:
        user_input_dialog = InputDialog(self)
        if user_input_dialog.exec():
            self.user_input = user_input_dialog.getInputs()
        else:
            # Dialog canceled or closed, so do nothing:
            return
        # Construct a dialog box to show while recording,
        # with a single button for "Finish recording":
        # Start streaming data from the board, save data to an output file:
        try:
            self.recorder.start(
                bidsroot=self.bidsroot,
                sub=self.user_input["sub"],
                ses=self.user_input["ses"],
                task=self.task["key"],
                run=self.user_input["run"],
                data_type=self.board["data_type"],
                modality=self.board["modality"],
                acq=self.user_input["acq"],
            )
        except Exception as e:
            QMessageBox.critical(self, "Recording not started!", str(e), QMessageBox.Ok)
            logging.exception("Failed to start recording! Full stack trace:")
            return
        try:
            # Show the recording dialog while recording is in process:
            self.recording_dialog = RecordingDialog(
                self
            )  # pass self as parent so we can access our OnOffWidget object attributes
            # Update widget status to "On"
            self.is_on = True
            self.update_button_state()
            self.finish = self.recording_dialog.exec()
            # Stop the recording when the user clicks
            # the Finish button on the recording dialog:
            if bool(self.finish):
                self.off()
        except Exception as e:
            QMessageBox.critical(self, "Recording not started!", str(e), QMessageBox.Ok)
            logging.exception("Failed to start recording! Full stack trace:")
            self.recorder.release()

    def off(self):
        """
        Called when Stop button is clicked.
        Stops streaming and releases the session with the board.
        """
        try:
            self.recorder.stop()
            # Switch the button to OFF state:
            self.is_on = False
            self.update_button_state()
            QMessageBox.information(
                self,
                "Recording saved!",
                "<b>Data saved to:</b> \n"
                + self.recorder.data_file_base
                + ".csv"
                + "\n <b>Located at:</b> \n"
                + self.recorder.data_path,
                QMessageBox.Ok,
            )
        except Exception:
            logging.exception("Failed to stop stream! Full stack trace:")

    def update_button_state(self):
        """
        Update the appearance of the control buttons (On/Off)
        depending on the current state.
        """
        if self.is_on:
            self.recordButton.setStyleSheet(
                "background-color: #D32F2F; color: #fff;"
            )  # Red when ON
            self.recordButton.setText("Recording ON")
            self.recordButton.setIcon(qta.icon("mdi.pulse", color="#fff"))
        else:
            if self.is_online:
                self.recordButton.setStyleSheet(
                    "background-color: #4CAF50; color: #fff;"
                )  # Green when OFF
                self.recordButton.setText("Start recording")
                self.recordButton.setIcon(
                    qta.icon("mdi.play-circle-outline", color="#fff")
                )
            else:
                self.recordButton.setIcon(qta.icon("mdi.minus-circle-off-outline"))


class InputDialog(QDialog):
    """Custom QDialog class for user input of BIDS field data before starting the recording."""

    def __init__(self, parent=None):
        super().__init__(parent)
        task = parent.task
        self.setWindowTitle("Enter data for this recording")
        # Construct the run input field:
        self.runField = QSpinBox(self)
        self.runField.setPrefix("run-")
        # Construct the subject input field:
        self.subjectField = QSpinBox(self)
        self.subjectField.setPrefix("sub-")
        # Construct the session input field:
        self.sessionField = QComboBox(self)
        # Add dropdown options using sessions key in config, if present:
        if "sessions" in task:
            for key, name in task["sessions"].items():
                self.sessionField.addItem(
                    name, key
                )  # adds all items in the .yml config file
            self.sessionField.setCurrentIndex(-1)  # default to blank option
        else:
            self.sessionField.addItem("Default", "defaultsession")
        # Construct the Acq. input field:
        self.acqField = QLineEdit(self)
        # Construct the form layout:
        layout = QFormLayout(self)
        layout.addRow("Subject", self.subjectField)
        layout.addRow("Session", self.sessionField)
        layout.addRow("Run", self.runField)
        layout.addRow("Acq", self.acqField)
        startButton = QPushButton("Start recording")
        startButton.setStyleSheet("background-color: #4CAF50; color: #fff;")
        startButton.setIcon(qta.icon("mdi.play-circle-outline", color="#fff"))
        cancelButton = QPushButton("Cancel")
        cancelButton.setIcon(qta.icon("mdi.close"))
        buttonBox = QDialogButtonBox(self)
        buttonBox.addButton(startButton, QDialogButtonBox.AcceptRole)
        buttonBox.addButton(cancelButton, QDialogButtonBox.RejectRole)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

    def getInputs(self):
        """Gets user input from dialog and returns it in a dict."""
        data = {
            "run": self.runField.cleanText(),
            "sub": self.subjectField.cleanText(),
            "ses": self.sessionField.currentData(),
            "acq": self.acqField.text(),
        }
        return data


class RecordingDialog(QDialog):
    """
    Custom QDialog class for showing current recording in-session,
    with a single button to finish (stop) the current recording.
    """

    def __init__(self, parent):
        super().__init__(parent)
        task = parent.task
        user_input = parent.user_input
        self.setWindowTitle("Recording in progress!")
        # Widget to store the grid:
        grid = QWidget()
        # Construct the layout:
        gridLayout = QGridLayout()
        # # Add field widgets to the layout:
        # # Grid row 0:
        gridLayout.addWidget(QLabel("<b>Output directory:</b>"), 0, 0)
        gridLayout.addWidget(QLabel(parent.recorder.data_path), 0, 1)
        # # Grid row 1:
        gridLayout.addWidget(QLabel("<b>Recording to file:</b>"), 1, 0)
        gridLayout.addWidget(QLabel(parent.recorder.data_file_base + ".csv"), 1, 1)
        # # Grid row 2:
        gridLayout.addWidget(QLabel("<b>Task:</b>"), 2, 0)
        if "label" in task:
            name = task["label"]
        else:
            name = task["key"]
        gridLayout.addWidget(QLabel(name), 2, 1)
        # # Grid row 3:
        gridLayout.addWidget(QLabel("<b>Subject:</b>"), 3, 0)
        gridLayout.addWidget(QLabel(user_input["sub"]), 3, 1)
        # # Grid row 4:
        gridLayout.addWidget(QLabel("<b>Session:</b>"), 4, 0)
        gridLayout.addWidget(QLabel(user_input["ses"]), 4, 1)
        # # Grid row 5:
        gridLayout.addWidget(QLabel("<b>Run</b>:"), 5, 0)
        gridLayout.addWidget(QLabel(user_input["run"]), 5, 1)
        # # Grid row 6:
        if "acq" in user_input and user_input["acq"] != "":
            gridLayout.addWidget(QLabel("<b>Acq:</b>"), 6, 0)
            gridLayout.addWidget(QLabel(user_input["acq"]), 6, 1)
        grid.setLayout(gridLayout)
        # Construct the progress bar:
        progressBar = QProgressBar(self)
        # Make the progress bar show as a 'busy' bar
        progressBar.setMinimum(0)
        progressBar.setMaximum(0)
        # Add the 'Finish recording' button to the recording dialog:
        finishButton = QPushButton("Finish recording")
        finishButton.setStyleSheet("background-color: #D32F2F; color: #fff;")
        finishButton.setIcon(qta.icon("mdi.stop-circle-outline", color="#fff"))
        buttonBox = QDialogButtonBox(self)
        buttonBox.addButton(finishButton, QDialogButtonBox.AcceptRole)
        # Place everything into a parent layout for the dialog window:
        mainLayout = QVBoxLayout(self)
        mainLayout.addWidget(grid)
        mainLayout.addWidget(progressBar)
        mainLayout.addWidget(
            QLabel(
                "<b>Recording to file:</b> " + parent.recorder.data_file_base + ".csv"
            )
        )
        mainLayout.addWidget(
            QLabel(
                "<b>Output directory:</b>\n"
                + os.path.realpath(parent.recorder.data_path)
            )
        )
        mainLayout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)

    def accept(self):
        """
        Shows a confirmation dialog asking the user to confirm before stopping
        the recording, to prevent accidental termination of recording-in-progress.
        """
        confirm_msg = "Are you sure you want to stop recording?"
        user_response = QMessageBox.question(
            self,
            "Confirm Finish Recording",
            confirm_msg,
            QMessageBox.Yes,
            QMessageBox.No,
        )
        if user_response == QMessageBox.Yes:
            # User answered Yes to the Confirm Finish Recording dialog,
            # so we call accept() on the parent (RecordingDialog) object:
            super().accept()

    def closeEvent(self, event):
        """Override the widget close event to prohibit closing the dialog window."""
        quit_msg = "You must finish the recording before closing this window."
        QMessageBox.warning(self, "Recording in progress!", quit_msg, QMessageBox.Ok)
        # Always ignore the close event on our RecordingDialog object,
        # to prevent accidental termination of recording-in-progress:
        event.ignore()


class BoardInfoWidget(QWidget):
    """Shows information about configured boards."""

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox = QVBoxLayout()
        board_manufacturer = ""
        # if "modelname" in parent.board["metadata"]:
        #     board_label = parent.board["metadata"]["modelname"]
        # else:
        board_label = parent.board["board_name"]
        # if "manufacturer" in parent.board["metadata"]:
        #   board_manufacturer = " by " + parent.board["metadata"]["manufacturer"]
        vbox.addWidget(QLabel(board_label + board_manufacturer))
        vbox.addWidget(QLabel(str(parent.recorder.sample_rate) + " Hz sampling rate"))
        vbox.addWidget(QLabel(str(parent.recorder.channel_count) + " channels"))
        if "params" in parent.board and "serial_port" in parent.board["params"]:
            vbox.addWidget(QLabel(parent.board["params"]["serial_port"]))
        self.setLayout(vbox)
        self.setStyleSheet(
            """
            QWidget {
                font-family: monospace;
                }
            """
        )


class QTextEditLogger(logging.Handler):
    """Custom widget class that shows the logger in the GUI."""

    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setStyleSheet(
            """
            QWidget {
                color: #D4D4D4;
                background-color: #1E1E1E;
                font-family: monospace;
                }
            """
        )

    def emit(self, record):
        """Inputs log data to GUI log textbox widget."""
        msg = self.format(record)
        self.widget.appendPlainText(msg)
