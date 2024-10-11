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
import Instructions_Reader

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
script_stop_flag = threading.Event()


class VideoThreadPiCam(QThread):
    """
    Thread class to run the camera on a different thread.
    """

    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, parent, status, host, port):
        """
        Constructs the thread.
        :param parent: invoker of thread.
        :param status: connection status, connected/disconnected
        :param host: the host of the server, (ip address)
        :param port: the port number
        """

        super().__init__(parent)
        self.connected = status
        self.client_socket = None
        self.host = host
        self.port = port
        self.grab_frame = True
        self.x = 0

    def run(self):
        """
        Runs the thread by connecting to the TCP socket receiving frames in bytes and decoding it
        using cv2, then displaying it onto the window.
        """

        BUFF_SIZE = 65536
        addr = (self.host, self.port)
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect(addr)
        buffer = b''
        # OBJ DETECT
        # model = torch.hub.load(r'D:\Documents\UoU\Spring24\ECE3992\ECE-Senior-Project\yolov5', 'custom', source='local', path='fire_v5n50e.pt', force_reload=True)
        # circle attr
        radius = 3
        thickness = -1
        color = (255, 0, 0)
        while not video_stop_flag.is_set():
            try:
                packet = self.client_socket.recv(BUFF_SIZE)
                buffer += packet
                while b'\0' in buffer:
                    # start = time.time()
                    message, buffer = buffer.split(b'\0', 1)
                    data = base64.b64decode(message)
                    frame = np.frombuffer(data, dtype=np.uint8)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

                    # OBJ DETECTION
                    # frame = cv2.resize(frame, (640, 480)) # (1920, 1080) (640, 480)
                    # results = model(frame)
                    # frame = np.squeeze(results.render())
                    # # x1(pixels), y1(pixels), x2(pixels), y2(pixels), confidence, class
                    # # print(results.xyxy)
                    # if len(results.xyxy[0]) > 0:
                    #     x1 = results.xyxy[0][0][0]
                    #     y1 = results.xyxy[0][0][1]
                    #     x2 = results.xyxy[0][0][2]
                    #     y2 = results.xyxy[0][0][3]
                    #
                    #     mid_x = (x1 + x2) / 2
                    #     mid_y = (y1 + y2) / 2
                    #
                    #     center_coordinate = (int(mid_x), int(mid_y))
                    #     frame = cv2.circle(frame, center_coordinate, radius, color, thickness)

                    self.change_pixmap_signal.emit(frame)

                    # FPS CHECK
                    # stop = time.time()
                    # print(str(stop-start), "ms")
            except Exception as e:
                pass
                # print(e)
        self.client_socket.close()


class LoggerThread(QThread):
    """
    Thread that updates the Log window with information.
    """

    update_signal = pyqtSignal(int, str)

    def __init__(self, parent, side, message):
        """
        Constructs the thread to display message on Log window.
        :param parent: invoker of thread
        :param side: the side of which the message is sent, client or server
        :param message: message to write to Log window
        """

        super().__init__(parent)
        self.side = side
        self.message = message

    def run(self):
        """
        Emits the signal by sending the message
        """

        self.update_signal.emit(self.side, self.message)


class ScriptWindow(QWidget):
    def __init__(self, main_window, log_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.width = 400
        self.height = 300
        # self.setGeometry(main_window.screen.width() - 418, main_window.screen.height() - 425, 400, 300) # hard code
        self.setGeometry(log_window.geometry().topRight().x() - self.width + 23,    # 23 is offset
                         log_window.geometry().topLeft().y() + log_window.geometry().height() + 125,
                         self.width,
                         self.height)
        self.setMinimumSize(self.width, self.height)
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
            self.main_window.log("Open error: " + str(e))

    def on_save_script(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(self, "Save File", "New_Script", "Text Files (*.txt)")
            with open(filename, 'w') as file:
                file.write(self.textBox.toPlainText())
        except Exception as e:
            self.main_window.log("Save error: " + str(e))

    def on_push_script(self):
        text = self.textBox.toPlainText()
        self.main_window.log(text)

    def toggle_script_window(self):
        self.main_window.toggle_write_script()

    def toggle_log_window(self):
        self.main_window.toggle_logger()


class LogWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.width = 300
        self.height = 400
        self.setGeometry(main_window.screen.width() - 335, main_window.screen.height() - 960, self.width, self.height)
        self.shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut.activated.connect(self.toggle_log_window)

        self.shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut.activated.connect(self.toggle_script_window)

        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Log Window")

        logs_l = QVBoxLayout()
        self.setLayout(logs_l)
        self.clearFocus()
        self.setFocusPolicy(Qt.NoFocus)

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
        self.logger.setMinimumSize(self.width, self.height)
        self.logger.setReadOnly(True)
        self.logger.setFocusPolicy(Qt.NoFocus)

        self.logger.setAlignment(Qt.AlignJustify)
        self.logger.setText("Welcome to RFES Control Center.")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

    def keyPressEvent(self, event):
        self.main_window.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.main_window.keyReleaseEvent(event)

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
        # self.setGeometry(0, 0, self.screen.width(), self.screen.height())
        self.showMaximized()
        self.setWindowIcon(QIcon('res/rfes_icon.png'))

        self.display_width = 1920
        self.display_height = 1080

        # main
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

        self.socket = None

        self.pi_battery = "0.00%"

        # where "1, 2, 3, 4, 5"
        self.water_level = "00000"
        self.wl_full = QPixmap("res/water_level/full_status.png")
        self.wl_down_one = QPixmap("res/water_level/down_one.png")
        self.wl_down_two = QPixmap("res/water_level/down_two.png")
        self.wl_down_three = QPixmap("res/water_level/down_three.png")
        self.wl_down_four = QPixmap("res/water_level/down_four.png")
        self.wl_empty_text = QPixmap("res/water_level/empty_with_text.png")
        self.wl_empty_no_text = QPixmap("res/water_level/empty_without_text.png")
        self.curr_wl = self.wl_empty_text
        self.mt_counter = 0

        self.feed_thread = None
        self.coms_thread = None
        self.recv_thread = None
        self.run_instr_thread = None

        self.defaultIP = str(HOST)
        self.defaultPort = str(PORT)
        self.status = "DISCONNECTED"

        self.keys = IDLE

        # mouse track
        self.is_tracking_mouse = False
        self.left_screen = 20
        self.right_screen = 1520
        self.top_screen = 185
        self.bot_screen = 1023

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

        self.log_window = LogWindow(self)
        self.script_window = ScriptWindow(self, self.log_window)

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

    # def mousePressEvent(self, event):
    #     """
    #     Gets the position of the mouse when it is clicked. For debugging purposes.
    #     :param event: action occurred
    #     :return: prints the coordinates of the mouse click
    #     """
    #     print('Mouse coords: ( %d : %d )' % (event.x(), event.y()))

    def mouseMoveEvent(self, event):
        """
        Tracks the movement of the mouse and bounds mouse to the window screen.
        :param event: the occuring event
        """

        if self.is_tracking_mouse:
            pwm_y_max = 10
            pwm_y_min = 5
            y = QCursor.pos().y()
            offset_y = y - self.top_screen  # 0 - 800
            percent_y = float(offset_y / (self.bot_screen - self.top_screen))
            percent_y_invert = 1 - percent_y
            pwm_y_value = ((pwm_y_max - pwm_y_min) * percent_y_invert) + pwm_y_min

            pwm_x_max = 10.4
            pwm_x_min = 7.5
            x = QCursor.pos().x()
            offset_x = x - self.left_screen
            percent_x = float(offset_x / (self.right_screen - self.left_screen))
            percent_x_invert = 1 - percent_x  # because of servos
            pwm_x_value = ((pwm_x_max - pwm_x_min) * percent_x_invert) + pwm_x_min

            if QCursor.pos().y() <= self.top_screen:
                QCursor.setPos(QPoint(QCursor.pos().x(), self.top_screen))
            elif QCursor.pos().y() >= self.bot_screen:
                QCursor.setPos(QPoint(QCursor.pos().x(), self.bot_screen))

            if QCursor.pos().x() >= self.right_screen:
                QCursor.setPos(QPoint(self.right_screen, QCursor.pos().y()))
            elif QCursor.pos().x() <= self.left_screen:
                QCursor.setPos(QPoint(self.left_screen, QCursor.pos().y()))

            self.keys = IDLE.copy()
            self.keys[9] = str(round(pwm_y_value, 2))
            self.keys[10] = str(round(pwm_x_value, 2))
            self.send_commands()

    def keyPressEvent(self, event):
        """
        Listens for any key pressed events.
        :param event: the type of event that occurs
        """

        key = event.key()
        if key == Qt.Key_M:
            if not self.is_tracking_mouse:
                self.is_tracking_mouse = True
                self.log(CLIENT, "SWITCHED TO MOUSE CONTROL.")
            else:
                self.is_tracking_mouse = False
                self.log(CLIENT, "SWITCHED TO KEYBOARD CONTROL.")

        if self.status == "DISCONNECTED":
            return

        self.keys = IDLE.copy()
        if not event.isAutoRepeat():
            if key == Qt.Key_W:
                self.keys[0] = '1'
            if key == Qt.Key_A:
                self.keys[1] = '1'
            if key == Qt.Key_S:
                self.keys[2] = '1'
            if key == Qt.Key_D:
                self.keys[3] = '1'
            if key == Qt.Key_Space:
                self.keys[4] = '1'
            if key == Qt.Key_Up:
                self.keys[5] = '1'
            if key == Qt.Key_Down:
                self.keys[6] = '1'
            if key == Qt.Key_Left:
                self.keys[7] = '1'
            if key == Qt.Key_Right:
                self.keys[8] = '1'
            if key == Qt.Key_I:
                self.run_instructions()
            self.send_commands()

    def keyReleaseEvent(self, event):
        """
        Listens for any key released events.
        :param event: type of event that occurs
        """

        if self.status == "DISCONNECTED":
            return

        key = event.key()
        self.keys = IDLE.copy()
        if not event.isAutoRepeat():
            if key == Qt.Key_W:
                self.keys[0] = '0'
            if key == Qt.Key_A:
                self.keys[1] = '0'
            if key == Qt.Key_S:
                self.keys[2] = '0'
            if key == Qt.Key_D:
                self.keys[3] = '0'
            if key == Qt.Key_Space:
                self.keys[4] = '0'
            if key == Qt.Key_Up:
                self.keys[5] = '0'
            if key == Qt.Key_Down:
                self.keys[6] = '0'
            if key == Qt.Key_Left:
                self.keys[7] = '0'
            if key == Qt.Key_Right:
                self.keys[8] = '0'
            self.send_commands()

    def send_commands(self):
        """
        Sends the commands inputted by user to the TCP server.
        """

        try:
            # self.socket.sendall((''.join(self.keys)).encode('utf-8'))
            keys_as_string = str(self.keys)[1: -1].replace(" ", "").replace("'", "").strip()
            self.send_packed_message(keys_as_string)

        except Exception as e:
            self.status = "DISCONNECTED"
            self.log(CLIENT, str(e))

    def send_packed_message(self, message):
        """
        Sends the message using the "prefixed with length" protocol.
        :param message: message to be sent
        """

        msg_len = len(message)
        self.socket.sendall(struct.pack("!I", msg_len))
        self.socket.sendall(message.encode('utf-8'))

    def recv_data(self):
        """
        Receives the data coming in following the "prefixed with length protocol.
        :returns the data that was received
        """

        raw_msg_len = self.socket.recv(4)  # get length of message

        if not raw_msg_len:
            return

        msg_len = struct.unpack("!I", raw_msg_len)[0]
        data = self.socket.recv(msg_len).decode('utf-8')
        return data

    def log_data(self):
        """
        Receives data from TCP server.
        """

        while True:
            try:
                data = str(self.recv_data())

                # filter data
                if data.startswith("/WL"):
                    self.water_level = data[3:]
                    continue
                elif data.startswith("/PIB"):
                    self.pi_battery = data[4:]
                else:
                    # set self.feed_thread.x to update to new ch pos
                    # if data is about servo movement, move the image instead.
                    recv_thread = LoggerThread(self, SERVER, data)
                    recv_thread.update_signal.connect(self.log)
                    recv_thread.start()
            except:
                print("server closed")
                break

    def connect_to_server(self):
        """
        Connects to the server and updates the connection status, logs it
        """

        self.connect_button.clearFocus()
        if self.status == "DISCONNECTED":
            print("connecting")
            self.log(CLIENT, "Connecting to server...")
            self.socket = socket(AF_INET, SOCK_STREAM)
            try:
                # threading.Thread(target=self.socket.connect, args=(self.ip_entry.text(), int(self.port_entry.text())))
                self.socket.connect((self.ip_entry.text(), int(self.port_entry.text())))
                self.log(SERVER, self.recv_data())
                self.recv_thread = threading.Thread(target=self.log_data, args=())
                self.recv_thread.start()
            except:
                print("ERROR")
                self.log(CLIENT, "Connection with RFES cannot be established. Try again.")
                return

            self.status = "CONNECTED"
            self.update_status()
            # Creates a new thread for the camera
            video_stop_flag.clear()  # resets flag
            self.feed_thread = VideoThreadPiCam(self, self.status, self.ip_entry.text(), int(
                self.port_entry.text()) + 1)
            # connect its signal to the update_image slot
            self.feed_thread.change_pixmap_signal.connect(self.update_image)
            # start the thread
            self.feed_thread.start()
            self.update()

        else:
            self.status = "DISCONNECTED"
            self.log(CLIENT, "Connection closed.")
            self.update_status()
            self.socket.close()

            # disables video thread
            video_stop_flag.set()

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """
        Updates the image_label with a new opencv image.
        """

        if self.status == "CONNECTED":
            qt_img = self.convert_cv_qt(cv_img)
            self.update_water_indicator()
            water_level = self.curr_wl.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.overlay_pixmaps(qt_img, water_level, self.display_width - 390, 25)
            self.feed.setPixmap(qt_img)
            self.feed_thread.grab_frame = True
        else:
            self.feed.setPixmap(QPixmap("res/not_connected.png"))
            self.update()

    def update_water_indicator(self):
        if self.water_level == "00000":
            if self.mt_counter >= 22:
                if self.curr_wl == self.wl_empty_no_text:
                    self.curr_wl = self.wl_empty_text
                    self.mt_counter = 0
                else:
                    self.curr_wl = self.wl_empty_no_text
                    self.mt_counter = 0
            self.mt_counter += 1
        else:
            if self.water_level[0] == "1":
                self.curr_wl = self.wl_down_one
                if self.water_level[1] == "1":
                    self.curr_wl = self.wl_down_two
                    if self.water_level[2] == "1":
                        self.curr_wl = self.wl_down_three
                        if self.water_level[3] == "1":
                            self.curr_wl = self.wl_down_four
                            if self.water_level[4] == "1":
                                self.curr_wl = self.wl_full

    def overlay_pixmaps(self, base_pixmap, overlay_pixmap, x=0, y=0):
        # Create a QPainter to paint on the base pixmap
        painter = QPainter(base_pixmap)

        # Draw the overlay pixmap on top of the base pixmap
        painter.drawPixmap(x, y, overlay_pixmap)

        # End the QPainter to save the changes
        painter.end()

        # Return the modified base pixmap
        return base_pixmap

    def convert_cv_qt(self, cv_img):
        """
        Convert from an opencv image to QPixmap.
        """

        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.display_width, self.display_height)  # Qt.KeepAspectRatio
        return QPixmap.fromImage(p)

    def run_instructions(self):
        """
        Starts the run_instr thread to run instrucitons.
        """
        instructions_path = "patrol.txt"  # should be from a field
        self.run_instr_thread = threading.Thread(target=self.execute_instructions, args=(instructions_path,))
        self.run_instr_thread.start()

    def execute_instructions(self, instructions_path):
        """
        Executes the instructions file by sending commands to RFES.
        :param instructions_path: file path
        """
        # NEEDS TO BE A ASYNC SINCE THIS HAS DELAY
        delay_between_commands = 0.1

        loop = 0
        in_loop_block = False
        execute_loop = False
        is_infinite_loop = False
        instructions_to_loop = []
        script_stop_flag.clear()

        instructions = Instructions_Reader.path_to_instructions(instructions_path)  # "["forward(10)", "left(90)", ...]"
        print(instructions)
        for instruction in instructions:
            if script_stop_flag.is_set():
                break
            inst = Instructions_Reader.instruction_as_tuple(instruction)  # "("forward", "10")"
            command = inst[0]  # forward
            value = inst[1]  # 10

            if not in_loop_block and command == "for":
                if value == "-1":
                    is_infinite_loop = True
                    loop = 1
                else:
                    loop = int(value)
                in_loop_block = True
                continue
            elif in_loop_block and command != "end":
                instructions_to_loop.append(inst)
                continue
            elif in_loop_block and command == "end":
                execute_loop = True
                in_loop_block = False
            if execute_loop:
                print(is_infinite_loop)
                i = 0
                while i < loop and not script_stop_flag.is_set():
                    for ins in instructions_to_loop:
                        if script_stop_flag.is_set():   # stop thread
                            break
                        command = ins[0]  # forward
                        value = float(ins[1])  # 10
                        self.send_script_instructions(command, value, delay_between_commands)
                    if not is_infinite_loop:
                        i += 1
                execute_loop = False
            else:
                value = float(value)  # 10
                self.send_script_instructions(command, value, delay_between_commands)

    def send_script_instructions(self, command, value, delay_between_commands):
        self.keys = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
        self.keys[Instructions_Reader.COMMANDS_STRING[command]] = ON
        print(self.keys)
        self.send_commands()
        if command in ["aim_left", "aim_right", "aim_up", "aim_down"]:  # if it's aiming, turn value to degrees
            # convert value to angle, so use value to see how long it takes to turn a certain angle
            time.sleep(value)  # right now it is still value as seconds
        else:
            time.sleep(value)  # value is treated as seconds
        self.keys = ['0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0']
        self.send_commands()
        print(self.keys)
        time.sleep(delay_between_commands)

    def update_status(self):
        """
        Updates the status of the connection.
        """

        if self.status == "DISCONNECTED":
            self.ip_entry.setReadOnly(False)
            self.ip_entry.setDisabled(False)

            self.port_entry.setReadOnly(False)
            self.port_entry.setDisabled(False)
            self.connect_button.setText("Connect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet(stylesheets.STATUS_LABEL_DISCONNECTED)

            # kill video thread
            # video_stop_flag.set()
            # self.feed_thread.join()

            # GUI update
            self.feed.setPixmap(QPixmap("res/not_connected.png"))
            self.update()

        else:
            self.ip_entry.setReadOnly(True)
            self.ip_entry.setDisabled(True)

            self.port_entry.setReadOnly(True)
            self.port_entry.setDisabled(True)

            self.connect_button.setText("Disconnect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet(stylesheets.STATUS_LABEL_CONNECTED)

            # self.bot_layout.removeWidget(self.feed)
            # self.feed.setParent(None)
            # self.bot_layout.insertWidget(0, self.browser)
            # create the video capture thread

    def on_open_script(self):
        # BROWSE FILES AND PRINT CONTENT OF FILE
        try:
            filename = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
            content = open(filename[0]).read()
            self.script_window.show()
            self.script_window.textBox.clear()
            self.script_window.textBox.setText(content)
        except Exception as e:
            self.log("Open error: " + str(e))

    def on_write_script(self):
        self.script_window.show()

    def toggle_write_script(self):
        if self.script_window.isVisible():
            self.script_window.hide()
        else:
            self.script_window.show()
            self.script_window.textBox.clear()

    def on_logger(self):
        self.log_window.show()

    def toggle_logger(self):
        if self.log_window.isVisible():
            self.log_window.hide()
        else:
            self.log_window.show()

    def log(self, side, text):
        self.log_window.log(side, text)

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
        self.ip_entry.setText(self.defaultIP)
        self.ip_entry.setPlaceholderText(self.defaultIP)
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
        self.port_entry.setText(str(self.defaultPort))
        self.port_entry.setPlaceholderText(str(self.defaultPort))
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
        self.connect_button.clicked.connect(self.connect_to_server)
        self.top_bar_layout.addWidget(self.connect_button)

        spacer = QSpacerItem(580, 5)
        self.top_bar_layout.addItem(spacer)

        # STATUS LABEL
        self.status_label = QLabel(self.status)
        self.status_label.setFixedHeight(20)
        self.status_label.setFont(fonts.STATUS_LABEL)
        self.status_label.setStyleSheet(stylesheets.STATUS_LABEL_DISCONNECTED)
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
        self.feed.setFixedSize(self.display_width, self.display_height)
        self.feed.setPixmap(QPixmap("res/not_connected.png"))
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
