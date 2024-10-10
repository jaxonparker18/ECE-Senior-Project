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

import cv2
import torch
import numpy as np
import base64
import time
import pathlib
import struct


class ScriptWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.toggleScriptWindow)

        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggleLogWindow)

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setMinimumSize(400, 300)
        self.setWindowTitle("Script Editor")
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(5)
        self.textBox = QTextEdit()
        # self.textBox.setPlaceholderText("Write your script here.")
        self.textBox.setPlaceholderText(
"AVAILABLE COMMANDS ARE: \n"
"// forward(x)\n"
"// backward(x)\n"
"// left(x)\n"
"// right(x)\n"
"// aim_up(s)\n"
"// aim_down(s)\n"
"// aim_left(s)\n"
"// aim_right(s)\n"
"// WHERE x IS THE VALUE FOR THE COMMAND\n"
"// AND s IS THE DEGREE OF THE TURN\n"
"// EXAMPLE:\n"
"// forward(10) where 10 is the duration of this command (in seconds)\n"
"//\n"
"// FOR AIMING COMMANDS:\n"
"// aim_up(90) where 90 is the angle to turn\n"
"//\n")
        self.submitButton = QPushButton("Push to submit and run code.")
        self.submitButton.clicked.connect(self.onPushScript)
        layout.addWidget(self.textBox)
        layout.addWidget(self.submitButton)
        self.setLayout(layout)

    def onPushScript(self, s):
        text = self.textBox.toPlainText()
        main_window.addToLogger(text)

    def toggleScriptWindow(self):
        main_window.onWriteScript()

    def toggleLogWindow(self):
        main_window.onLogger()

class LogWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggleLogWindow)

        self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.toggleScriptWindow)

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

        # logs_l.addWidget(logger_label)

        self.logger = QTextBrowser(self)
        self.logger.setMinimumSize(300, 400)
        self.logger.setReadOnly(True)
        self.logger.setFocusPolicy(Qt.NoFocus)

        self.logger.setAlignment(Qt.AlignJustify)
        self.logger.setText("Welcome to RFES Control Center.")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

    def toggleLogWindow(self):
        main_window.onLogger()

    def toggleScriptWindow(self):
        main_window.onWriteScript()


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

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.setStyleSheet("background-color: rgb(255, 116, 24);")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

        self.top_bar()
        self.main_feed()

        # new
        self.scriptWindow = ScriptWindow()
        self.logWindow = LogWindow()

        # QAction for open txt script.
        open_script_action = QAction(QIcon("controller.png"), "Open Script", self)
        open_script_action.setStatusTip("Opens script written in custom RFES language.")
        open_script_action.triggered.connect(self.onOpenScript)
        open_script_action.setShortcut(Qt.CTRL + Qt.Key_O)

        # QAction for write script.
        open_write_script_action = QAction(QIcon("controller.png"), "Write Script", self)
        open_write_script_action.setStatusTip("Opens field to write custom RFES language script.")
        open_write_script_action.triggered.connect(self.onWriteScript)
        open_write_script_action.setShortcut(Qt.CTRL + Qt.Key_S)

        # QAction for logger.
        open_logger_action = QAction(QIcon("controller.png"), "Open Log", self)
        open_logger_action.setStatusTip("Opens logger to see updated information.")
        open_logger_action.triggered.connect(self.onLogger)
        open_logger_action.setShortcut(Qt.CTRL + Qt.Key_L)

        # Initialize StatusBar and MenuBar
        self.setStatusBar(QStatusBar(self))
        menu = self.menuBar()

        # MenuBar Setup
        file_menu = menu.addMenu("&File")
        file_menu.addAction(open_script_action)
        file_menu.addAction(open_write_script_action)
        file_menu.addAction(open_logger_action)


    # ========================
    def onOpenScript(self):
        # BROWSE FILES AND PRINT CONTENT OF FILE
        try:
            filename = QFileDialog.getOpenFileName(self, 'Open File', 'C:/Users/Owner/Desktop', 'TXT Files (*.txt)')
            content = open(filename[0]).read()
            print("Reading from file: " + filename[0])
            print(content)
        except Exception as e:
            print("Error: " + str(e))

    def onWriteScript(self):
        if self.scriptWindow.isVisible():
            self.scriptWindow.hide()
        else:
            self.scriptWindow.show()
            self.scriptWindow.textBox.clear()

    def onLogger(self):
        if self.logWindow.isVisible():
            self.logWindow.hide()
        else:
            self.logWindow.show()

    def addToLogger(self, text):
        self.logWindow.log(0, text)

    def top_bar(self):
        self.top_bar_widget = QWidget()
        self.top_bar_layout = QHBoxLayout()
        self.top_bar_widget.setLayout(self.top_bar_layout)
        # self.top_bar_widget.setStyleSheet("border: 3px solid black;")     # comment when done
        self.top_bar_layout.setSpacing(0)
        self.top_bar_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.top_bar_widget)

        # IP
        ip_label = QLabel("IP:")
        ip_label.setFixedHeight(20)
        ip_label.setContentsMargins(0, 0, 0, 0)
        font = QFont("sans serif", 13)
        font.setBold(True)
        ip_label.setFont(font)
        self.top_bar_layout.addWidget(ip_label)
        self.ip_entry = QLineEdit()
        self.ip_entry.setFixedSize(250, 20)
        self.ip_entry.setFont(QFont("sans serif", 12))
        self.ip_entry.setStyleSheet("border: 2px solid black;")
        self.top_bar_layout.addWidget(self.ip_entry)

        # SPACER
        spacer = QSpacerItem(100, 5)
        self.top_bar_layout.addItem(spacer)

        # PORT
        port_label = QLabel("Port:")
        port_label.setFixedHeight(20)
        port_label.setContentsMargins(0, 0, 0, 0)
        font = QFont("sans serif", 13)
        font.setBold(True)
        port_label.setFont(font)
        self.top_bar_layout.addWidget(port_label)
        self.port_entry = QLineEdit()
        self.port_entry.setFixedSize(200, 20)
        self.port_entry.setFont(QFont("sans serif", 12))
        self.port_entry.setStyleSheet("border: 2px solid black;")
        self.top_bar_layout.addWidget(self.port_entry)

        spacer = QSpacerItem(200, 5)
        self.top_bar_layout.addItem(spacer)

        # CONNECT BUTTON
        self.connect_button = QPushButton("Connect")
        self.setContentsMargins(0, 0, 0, 0)
        self.connect_button.setFixedSize(200, 25)
        self.connect_button.setFont(QFont("sans serif", 12))
        self.connect_button.setStyleSheet("QPushButton {"
                                          "background-color: rgb(50, 50, 50); "
                                          "color: rgb(255, 255, 255);"
                                          "}"
                                          "QPushButton::pressed {"
                                          "background-color: rgb(100, 100, 100);"
                                          "}")
        self.top_bar_layout.addWidget(self.connect_button)

        spacer = QSpacerItem(550, 5)
        self.top_bar_layout.addItem(spacer)

        # STATUS LABEL
        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setFixedHeight(20)
        font = QFont("sans serif", 19)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: rgb(255, 0, 0);")
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

        # Line
        # line = QLabel()
        # line.setFixedSize(self.screen.width(), 3)
        # line.setStyleSheet("border: 3px solid black;")
        # self.main_layout.addWidget(line)

        self.main_layout.addWidget(self.center_widget)

        self.feed = QLabel()
        self.feed.setContentsMargins(0, 0, 0, 0)
        self.feed.setStyleSheet("QLabel { background-color : rgb(255, 116, 24);}")
        self.feed.setFixedSize(self.screen.width(), self.screen.height())
        self.feed.setPixmap(QPixmap("res/not_connected.png"))
        self.feed.setAlignment(Qt.AlignCenter)


        self.center_layout.addWidget(self.feed)


myappid = 'rfes-control-center'  # arbitrary string
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
sys.exit(app.exec_())
