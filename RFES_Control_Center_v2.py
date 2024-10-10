import os
import traceback
from datetime import datetime
import sys
from socket import *
import multiprocessing
import threading

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import *
import ctypes
import res.Stylesheets as stylesheets
import res.Fonts as fonts

import cv2
import torch
import numpy as np
import base64
import time
import pathlib
import struct

# main_window = None

# GLOBAL VARIABLES
HOST = "10.42.0.1"
# HOST = "169.254.196.32"  # The server's hostname or IP address
# Pi server = 172.20.10.3
PORT = 2100  # The port used by the server, must be >= 1024

# constants
CLIENT = 0
SERVER = 1

# corresponds to [W, A, S, D, spacebar, up, down, left, right, m_y, m_x]
IDLE = ['x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x', 'x']
OFF_KEYS  = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']

ON = '1'
OFF = '0'
DC = 'x'
# thread stop flags
video_stop_flag = threading.Event()
recv_stop_flag = threading.Event()


class ScriptWindow(QWidget):
    def __init__(self, main_window, screen):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setGeometry(screen.width() - 418, screen.height() - 425, 400, 300)
        self.setMinimumSize(400, 300)
        self.setWindowTitle("Script Editor")

        self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.toggle_script_window)

        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggle_log_window)

        # menubar
        menu = QMenuBar(self)

        # QAction for open txt script.
        open_script_action = QAction("Open Script", self)
        open_script_action.setStatusTip("Opens script written in custom RFES language.")
        open_script_action.triggered.connect(self.on_open_script)

        # QAction for save txt script.
        save_script_action = QAction("Save Script", self)
        save_script_action.setStatusTip("Saves script written in custom RFES language.")
        save_script_action.triggered.connect(self.on_save_script)

        # MenuBar Setup
        file_menu = menu.addMenu("&File")
        file_menu.addAction(open_script_action)
        file_menu.addAction(save_script_action)

        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(5)
        self.textBox = QTextEdit()
        self.textBox.setPlaceholderText(
            "AVAILABLE COMMANDS ARE: \n"
            "forward(x)\n"
            "backward(x)\n"
            "left(x)\n"
            "right(x)\n"
            "aim_up(s)\n"
            "aim_down(s)\n"
            "aim_left(s)\n"
            "aim_right(s)\n"
            "WHERE x IS THE VALUE FOR THE COMMAND\n"
            "AND s IS THE DEGREE OF THE TURN\n"
            "\n"
            "EXAMPLE:\n"
            "forward(10) where 10 is the duration of this command (in seconds)\n"
            "\n"
            "FOR AIMING COMMANDS:\n"
            "aim_up(90) where 90 is the angle to turn\n"
            "\n")
        self.submitButton = QPushButton("Push to submit and run code.")
        self.submitButton.clicked.connect(self.on_push_script)
        layout.addWidget(self.textBox)
        layout.addWidget(self.submitButton)
        self.setLayout(layout)
        layout.setMenuBar(menu)

    def on_open_script(self):
        # BROWSE FILES AND PRINT CONTENT OF FILE
        try:
            filename = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
            content = open(filename[0]).read()
            self.textBox.setText(content)
        except Exception as e:
            self.main_window.add_to_logger("Open error: " + str(e))

    def on_save_script(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(self, "Save File", "New_Script", "Text Files (*.txt)")
            with open(filename, 'w') as file:
                file.write(self.textBox.toPlainText())
        except Exception as e:
            self.main_window.add_to_logger("Save error: " + str(e))

    def on_push_script(self):
        text = self.textBox.toPlainText()
        self.main_window.add_to_logger(text)

    def toggle_script_window(self):
        self.main_window.toggle_write_script()

    def toggle_log_window(self):
        self.main_window.toggle_logger()


class LogWindow(QWidget):
    def __init__(self, main_window, screen):
        super().__init__()
        self.main_window = main_window

        self.setGeometry(screen.width() - 340, screen.height() - 960, 300, 400)

        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggle_log_window)

        self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.toggle_script_window)

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Log Window")

        logs_l = QVBoxLayout()
        self.setLayout(logs_l)

        # TOP ROW OF LOGS
        logs_top_w = QWidget()
        logs_top_l = QHBoxLayout()
        logs_top_w.setLayout(logs_top_l)

        logger_label = QLabel("Logs")
        logger_label.setFont(QFont("sans serif", 12))
        logs_top_l.addWidget(logger_label)

        clear_log_button = QPushButton()
        clear_log_button.setText("Clear logs")
        clear_log_button.setFixedSize(100, 30)
        clear_log_button.clicked.connect(lambda: self.logger.setText(""))
        logs_top_l.addWidget(clear_log_button)

        logs_l.addWidget(logs_top_w)

        self.logger = QTextBrowser(self)
        self.logger.setMinimumSize(300, 400)
        self.logger.setReadOnly(True)
        self.logger.setFocusPolicy(Qt.NoFocus)

        self.logger.setAlignment(Qt.AlignJustify)
        self.logger.setText("Welcome to RFES Control Center.")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

    def toggle_log_window(self):
        self.main_window.toggle_logger()

    def toggle_script_window(self):
        self.main_window.toggle_write_script()

    def log(self, side, message):
        """
        Logs information onto the Log window along with the time.
        :param side: message source, client/server
        :param message: the message to be logged
        """
        time = datetime.now().strftime("%H:%M:%S")
        if side == 0:
            self.logger.setText(str(self.logger.toPlainText()) + (
                "\n" if self.logger.toPlainText() != "" else "") + time + " - CLIENT: " + message)
        else:
            self.logger.setText(str(self.logger.toPlainText()) + (
                "\n" if self.logger.toPlainText() != "" else "") + time + " - SERVER: " + message)
        self.logger.verticalScrollBar().setValue(
            self.logger.verticalScrollBar().maximum()
        )


class MainWindow(QMainWindow):
    """
    The main window that is displayed upon code execution.
    """

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("RFES Control Center")
        self.screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, self.screen.width(), self.screen.height())
        self.showMaximized()
        self.setWindowIcon(QIcon('res/rfes_icon.png'))

        self.top_bar_widget = None
        self.top_bar_layout = None
        self.center_widget = None
        self.center_layout = None

        # top bar
        self.ip_entry = None
        self.port_entry = None
        self.connect_button = None
        self.status_label = None

        # center
        self.feed = None

        # main widget setup
        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet(stylesheets.MAIN)

        # function calls to set up components
        self.top_bar()
        self.main_feed()

        self.scriptWindow = ScriptWindow(self, self.screen)
        self.logWindow = LogWindow(self, self.screen)

        # QAction for open txt script.
        open_script_action = QAction(QIcon("controller.png"), "Open Script", self)
        open_script_action.setStatusTip("Opens script written in custom RFES language.")
        open_script_action.triggered.connect(self.on_open_script)
        open_script_action.setShortcut(Qt.CTRL + Qt.Key_O)

        # QAction for write script.
        open_write_script_action = QAction(QIcon("controller.png"), "Write Script (Ctrl + S)", self)
        open_write_script_action.setStatusTip("Opens field to write custom RFES language script.")
        open_write_script_action.triggered.connect(self.on_write_script)
        open_write_script_action.setShortcut("Ctrl+S")

        # QAction for logger.
        open_logger_action = QAction(QIcon("controller.png"), "Open Log (Ctrl + L)", self)
        open_logger_action.setStatusTip("Opens logger to see updated information.")
        open_logger_action.triggered.connect(self.on_logger)
        open_logger_action.setShortcut("Ctrl+L")

        # Initialize StatusBar and MenuBar
        status_bar = self.statusBar()
        status_bar.setStyleSheet(stylesheets.STATUS_BAR)
        menu = self.menuBar()

        # MenuBar Setup
        file_menu = menu.addMenu("&File")
        file_menu.addAction(open_script_action)
        file_menu.addAction(open_write_script_action)
        file_menu.addAction(open_logger_action)

        # Focus
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def on_open_script(self):
        # BROWSE FILES AND PRINT CONTENT OF FILE
        try:
            filename = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
            content = open(filename[0]).read()
            self.scriptWindow.show()
            self.scriptWindow.textBox.clear()
            self.scriptWindow.textBox.setText(content)
        except Exception as e:
            self.add_to_logger("Open error: " + str(e))

    def on_write_script(self):
        self.scriptWindow.show()

    def toggle_write_script(self):
        if self.scriptWindow.isVisible():
            self.scriptWindow.hide()
        else:
            self.scriptWindow.show()
            self.scriptWindow.textBox.clear()

    def on_logger(self):
        self.logWindow.show()

    def toggle_logger(self):
        if self.logWindow.isVisible():
            self.logWindow.hide()
        else:
            self.logWindow.show()

    def add_to_logger(self, text):
        self.logWindow.log(0, text)

    def top_bar(self):
        # Line
        line = QLabel()
        line.setFixedSize(self.screen.width(), 3)
        line.setStyleSheet(stylesheets.LINE_SEPARATOR)
        self.main_layout.addWidget(line)

        self.top_bar_widget = QWidget()
        self.top_bar_layout = QHBoxLayout()
        self.top_bar_widget.setLayout(self.top_bar_layout)
        self.top_bar_widget.setStyleSheet(stylesheets.TOP_BAR)
        self.top_bar_layout.setSpacing(0)
        self.top_bar_layout.setContentsMargins(15, 2, 0, 3)
        self.main_layout.addWidget(self.top_bar_widget)

        # IP
        ip_label = QLabel("IP:")
        ip_label.setFixedHeight(20)
        ip_label.setContentsMargins(0, 0, 5, 0)
        ip_label.setFont(fonts.IP_LABEL)
        self.top_bar_layout.addWidget(ip_label)
        self.ip_entry = QLineEdit()
        self.ip_entry.setPlaceholderText(HOST)
        self.ip_entry.setText(HOST)
        self.ip_entry.setFixedSize(250, 25)
        self.ip_entry.setFont(fonts.IP_ENTRY)
        self.ip_entry.setStyleSheet(stylesheets.IP_ENTRY)
        self.top_bar_layout.addWidget(self.ip_entry)

        # SPACER
        spacer = QSpacerItem(100, 5)
        self.top_bar_layout.addItem(spacer)

        # PORT
        port_label = QLabel("Port:")
        port_label.setFixedHeight(20)
        port_label.setContentsMargins(0, 0, 5, 0)
        port_label.setFont(fonts.PORT_LABEL)
        self.top_bar_layout.addWidget(port_label)
        self.port_entry = QLineEdit()
        self.port_entry.setText(str(PORT))
        self.port_entry.setPlaceholderText(str(PORT))
        self.port_entry.setFixedSize(130, 25)
        self.port_entry.setFont(fonts.PORT_ENTRY)
        self.port_entry.setStyleSheet(stylesheets.PORT_ENTRY)
        self.top_bar_layout.addWidget(self.port_entry)

        spacer = QSpacerItem(325, 5)
        self.top_bar_layout.addItem(spacer)

        # CONNECT BUTTON
        self.connect_button = QPushButton("Connect")
        self.connect_button.setContentsMargins(0, 0, 0, 0)
        self.connect_button.setFixedSize(200, 25)
        self.connect_button.setFont(fonts.CONNECT_BUTTON)
        self.connect_button.setStyleSheet(stylesheets.CONNECT_BUTTON)
        self.top_bar_layout.addWidget(self.connect_button)

        spacer = QSpacerItem(580, 5)
        self.top_bar_layout.addItem(spacer)

        # STATUS LABEL
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setFixedHeight(20)
        self.status_label.setFont(fonts.STATUS_LABEL)
        self.status_label.setStyleSheet(stylesheets.STATUS_LABEL)
        self.top_bar_layout.addWidget(self.status_label)

        # left align
        self.top_bar_layout.addStretch(1)

    def main_feed(self):
        """
        Displays the disconnected icon when currently disconnected.
        """

        self.center_widget = QWidget()
        self.center_layout = QVBoxLayout()
        self.center_widget.setLayout(self.center_layout)
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.setSpacing(0)

        # Line
        line = QLabel()
        line.setFixedSize(self.screen.width(), 3)
        line.setStyleSheet(stylesheets.LINE_SEPARATOR)
        self.main_layout.addWidget(line)

        self.main_layout.addWidget(self.center_widget)

        self.feed = QLabel()
        self.feed.setContentsMargins(0, 0, 0, 0)
        self.feed.setStyleSheet(stylesheets.FEED_LABEL)
        self.feed.setScaledContents(True)
        self.feed.setPixmap(QPixmap("res/samplefeed.jpg"))
        self.feed.setAlignment(Qt.AlignCenter)
        self.center_layout.addWidget(self.feed)


def main():
    myappid = 'rfes-control-center'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
