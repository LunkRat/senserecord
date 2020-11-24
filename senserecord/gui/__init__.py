import argparse
import logging
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QFileDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QAction,
    QMessageBox,
    QToolBar,
    QSizePolicy,
)
import qtawesome as qta
from pyshortcuts import make_shortcut
from senserecord.gui.widgets import OnOffWidget, BoardInfoWidget, QTextEditLogger
from senserecord.core import process_yaml


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # Parse incoming command line arguments:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--config",
            type=str,
            help="Local path to a YAML file (.yml, .yaml) containing configuration settings",
            required=False,
            default="",
        )
        parser.add_argument(
            "--task",
            type=str,
            help="Name for the task that the subject performs while connected to the biosensor",
            required=False,
            default="",
        )
        parser.add_argument(
            "--board",
            type=str,
            help="Board name of a BrainFlow supported board",
            required=False,
            default="",
        )
        parser.add_argument(
            "--serial-port",
            type=str,
            help="local serial port to use when communicating with the board",
            required=False,
            default="",
        )
        args = parser.parse_args()

        if args.config:
            self.config_file = args.config
        if args.task and args.config:
            parser.error(
                "--task cannot be combined with --config. Instead, specify your task in your config file."
            )
        if args.task and not args.board:
            parser.error("--task requires that you also specify --board")
        # if args.board and not args.serial_port:
        #     parser.error('--board requires that you also specify --serial-port')
        if args.serial_port and not args.board:
            parser.error("--serial-port requires that you also specify --board")
        if args.task:
            taskname = args.task
        else:
            # Set task to 'default' if none given:
            taskname = "default"
        if args.board:
            # If a board name was given as a cli argument,
            # set bare minimum config from cli arguments:
            self.config = {
                "tasks": {
                    taskname: {
                        "boards": {
                            args.board: {
                                "name": args.board,
                            }
                        }
                    }
                }
            }
        if args.serial_port:
            self.config["tasks"][taskname]["boards"][args.board]["params"] = {
                "serial_port": args.serial_port
            }
        # Logger box:
        logTextBox = QTextEditLogger(self)
        logTextBox.setFormatter(
            logging.Formatter("%(asctime)s - %(module)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(logTextBox)
        # Logging level control:
        logging.getLogger().setLevel(logging.DEBUG)
        loglabel = QLabel()
        loglabel.setText("Log output:")
        loglabel.setBuddy(logTextBox.widget)
        # Main info area container (top of main window).
        self.task_panel = QWidget()
        self.taskLayout = QHBoxLayout()
        # Main control panel container (center of main window).
        self.controls = QWidget()
        self.controlsLayout = QVBoxLayout()
        # Main container.
        container = QWidget()
        containerLayout = QVBoxLayout()
        containerLayout.addWidget(self.task_panel)
        containerLayout.addWidget(self.controls)
        containerLayout.addWidget(loglabel)
        containerLayout.addWidget(logTextBox.widget)
        container.setLayout(containerLayout)
        self.setCentralWidget(container)
        # Set initial window width:
        self.setMinimumWidth(1000)
        # Window title:
        self.setWindowTitle("Sense Record")
        # Construct status bar (bottom of MainWindow):
        self.statusBar()
        # Construct Menu bar on MainWindow:
        menubar = self.menuBar()
        # File menu
        fileMenu = menubar.addMenu("&File")
        # File > Load config:
        loadAct = QAction(qta.icon("mdi.folder-cog-outline"), "&Load config file", self)
        loadAct.setShortcut("Ctrl+O")
        loadAct.setStatusTip("Load configuration data from a .yml file")
        loadAct.triggered.connect(self.get_config_file)
        fileMenu.addAction(loadAct)
        # Tasks menu
        self.tasksMenu = menubar.addMenu("&Tasks")
        # View menu
        self.viewMenu = menubar.addMenu("&View")
        self.refreshAct = QAction(qta.icon("mdi.refresh"), "Refresh", self)
        self.refreshAct.setStatusTip(
            "Refresh the task into and board status in the controls."
        )
        self.refreshAct.triggered.connect(self.load_config)
        self.refreshAct.setDisabled(True)
        self.viewMenu.addAction(self.refreshAct)
        # Toolbar
        self.toolbar = QToolBar("Main toolbar")
        self.addToolBar(self.toolbar)
        # Load configuration if present
        if hasattr(self, "config_file") or args.board:
            self.load_config()
        else:
            # Config file button and file dialog.
            btn_config = QPushButton(
                qta.icon("mdi.folder-cog-outline"), "Select config file ..."
            )
            btn_config.clicked.connect(self.get_config_file)
            self.toolbar.addWidget(
                QLabel("You must select a config file to load controls.")
            )
            self.controlsLayout.addWidget(btn_config)
        # Set the controls (for the heart of the sun):
        self.controls.setLayout(self.controlsLayout)

    def set_controls(self, name: str):
        """Generates the labels and controls that appear in the controls area."""

        # Clear the current toolbar:
        self.toolbar.clear()
        # Clear the current task panel:
        self.clear_layout(self.taskLayout)
        # Clear the current controls:
        self.clear_layout(self.controlsLayout)
        # Enable the refresh menu action in the View menu:
        self.refreshAct.setDisabled(False)
        # Load our task from global config:
        self.task = self.config["tasks"][name]
        # Make the toolbar items:
        if "label" in self.task:
            label_text = self.task["label"]
        else:
            label_text = name
        taskLabel = QLabel(chr(0xF10D5) + " " + "<strong>Task: </strong>" + label_text)
        taskLabel.setFont(qta.font("fa", 26))

        self.toolbar.addWidget(taskLabel)
        toolbarSpacer = QWidget(self)  # right-aligns the refresh button
        toolbarSpacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        refreshButton = QAction(qta.icon("mdi.refresh"), "Refresh", self)
        refreshButton.setStatusTip(
            "Refresh the task into and board status in the controls."
        )
        refreshButton.triggered.connect(self.load_config)
        self.toolbar.addWidget(toolbarSpacer)
        self.toolbar.addAction(refreshButton)
        # Make the task info panel:
        if "description" in self.task:
            taskLabel.setToolTip(self.task["description"])
            taskDescription = QWidget()
            taskDescription.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
            descriptionLayout = QVBoxLayout()
            descriptionLayout.setAlignment(Qt.AlignTop)
            descriptionLabel = QLabel(self.task["description"])
            descriptionLabel.setWordWrap(True)
            descriptionHeading = QLabel(
                chr(0xF0EA7) + " " + "<strong>Description: </strong>"
            )
            descriptionHeading.setFont(qta.font("fa", 26))
            descriptionLayout.addWidget(descriptionHeading)
            descriptionLayout.addWidget(descriptionLabel)
            taskDescription.setLayout(descriptionLayout)
            self.taskLayout.addWidget(taskDescription, 6)
        if "sessions" in self.task:
            taskSessions = QWidget()
            sessionLayout = QVBoxLayout()
            sessionLayout.setAlignment(Qt.AlignTop)
            sessionsHeading = QLabel(chr(0xF0ED8) + " " + "<strong>Sessions: </strong>")
            sessionsHeading.setFont(qta.font("fa", 26))
            sessionLayout.addWidget(sessionsHeading)
            for k, v in self.task["sessions"].items():
                sessionLayout.addWidget(QLabel(v))
            taskSessions.setLayout(sessionLayout)
            self.taskLayout.addWidget(taskSessions, 6)
        else:
            spacer = QWidget(self)
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.taskLayout.addWidget(spacer, 6)
        # Refresh the task info panel layout:
        self.task_panel.setLayout(self.taskLayout)
        # Make controls for self.task:
        self.task["key"] = name  # Insert task id key to the task dict
        # Construct on/off button controls for each board in our task:
        for board, settings in self.task["boards"].items():
            widget_config = {"key": board, "board": settings, "task": self.task}
            # pass our preprocessed button config to each new OnOffWidget
            # object we add to the layout:
            self.controlsLayout.addWidget(OnOffWidget(widget_config))
        self.controls.setLayout(self.controlsLayout)

    def set_tasks_menu(self):
        """Generates the items for the Tasks menu."""

        self.tasksMenu.clear()
        for name, settings in self.config["tasks"].items():
            taskAct = QAction(qta.icon("mdi.clipboard-list-outline"), "&" + name, self)
            taskAct.setStatusTip("Load controls for " + name)
            # https://stackoverflow.com/questions/6784084/how-to-pass-arguments-to-functions-by-the-click-of-button-in-pyqt
            taskAct.triggered.connect(lambda state, x=name: self.set_controls(x))
            self.tasksMenu.addAction(taskAct)

    def get_config_file(self):
        """Shows a file browser dialog to set active config file."""

        config_file = QFileDialog.getOpenFileName(
            self, ("Open Config File"), "./", ("YAML files (*.yml *.yaml)")
        )
        if config_file[0]:
            # Path to the yml:
            self.config_file = config_file[0]
            # Ingest the config from yml:
            self.load_config()

    def load_config(self):
        """Loads data from config file and calls functions
        to update window using new data from config file."""

        if hasattr(self, "config_file"):
            try:
                self.config = process_yaml(self.config_file)
                logging.info("Using configuration loaded from " + self.config_file)
                self.statusBar().showMessage("Active config file: " + self.config_file)
            except Exception as e:
                QMessageBox.critical(
                    self, "Invalid config file!", str(e), QMessageBox.Ok
                )

        first_taskname = list(self.config["tasks"].keys())[0]
        self.set_controls(first_taskname)  # default to first task when loading config
        self.set_tasks_menu()

    def clear_layout(self, layout):
        """Recursively deletes all widgets in given layout."""

        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def closeEvent(self, event):
        """
        Overrides inherited closeEvent method to inject a
        confirmation dialog when MainWindow is closed.
        """

        quit_msg = "Are you sure you want to exit?"
        reply = QMessageBox.question(
            self, "Quit Application", quit_msg, QMessageBox.Yes, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
