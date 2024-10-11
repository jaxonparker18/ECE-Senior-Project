# echo-client.py
# LAST UPDATE: Nathan - 8/27/2024 - 3:19 PM
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

import Instructions_Reader

temp = pathlib.PosixPath
pathlib.PosixPath = pathlib.WindowsPath

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


class MainWindow(QWidget):
    """
    The main window that is displayed upon code execution.
    """

    def __init__(self):
        """
        Constructs the window that is displayed.
        """

        super(MainWindow, self).__init__()
        self.logger = None
        self.status_label = None
        # self.setStyleSheet("background-color: #202124;")    # for dark mode
        self.setWindowTitle("RFES Control Center")
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width(), screen.height())
        self.showMaximized()
        self.setWindowIcon(QIcon('res/rfes_icon.png'))

        self.ip_entry = QLineEdit()
        self.port_entry = QLineEdit()
        self.c_d_button = QPushButton()

        self.socket = None
        self.browser = None
        self.feed = None
        self.feed_thread = None
        self.coms_thread = None
        self.recv_thread = None
        self.run_instr_thread = None

        # mouse track
        self.is_tracking_mouse = False
        self.left_screen = 20
        self.right_screen = 1520
        self.top_screen = 185
        self.bot_screen = 1023

        # corresponds to [W, A, S, D, spacebar, up, down, left, right, m_y, m_x]
        self.keys = IDLE

        self.display_width = 1500
        self.display_height = 840

        # default values
        self.defaultIP = str(HOST)
        self.defaultPort = str(PORT)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Top panel
        self.top_widget = QWidget()
        self.top_panel_layout = QHBoxLayout()
        self.top_widget.setLayout(self.top_panel_layout)

        # Top panel, left side (FIELDS, C/D BUTTON)
        self.TL_widget = QWidget()
        self.TL_layout = QHBoxLayout()
        self.TL_layout.setAlignment(Qt.AlignLeft)
        self.TL_widget.setLayout(self.TL_layout)

        # Top panel, right side (STATUS)
        self.TR_widget = QWidget()
        self.TR_layout = QVBoxLayout()
        self.TR_layout.setAlignment(Qt.AlignRight)
        self.TR_widget.setLayout(self.TR_layout)

        self.top_panel_layout.addWidget(self.TL_widget)
        self.top_panel_layout.addWidget(self.TR_widget)

        self.layout.addWidget(self.top_widget)

        # Bottom panel
        self.bot_widget = QWidget()
        self.bot_layout = QHBoxLayout()
        self.bot_widget.setLayout(self.bot_layout)

        self.layout.addWidget(self.bot_widget)

        self.status = "DISCONNECTED"

        # initialize all components
        self.create_label_panel()
        self.create_entry_panel()
        self.show_status()
        self.display_disconnected()
        self.display_logs()
        self.create_connect_disconnect_panel()

        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

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

    def send_commands(self):
        """
        Sends the commands inputted by user to the TCP server.
        """

        try:
            # self.socket.sendall((''.join(self.keys)).encode('utf-8'))
            keys_as_string = str(self.keys)[1: -1].replace(" ", "").replace("'", "").strip()
            self.send_packed_message(keys_as_string)

        except:
            self.status = "DISCONNECTED"

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
                data = self.recv_data()
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

        self.c_d_button.clearFocus()
        if self.status == "DISCONNECTED":
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

    def display_disconnected(self):
        """
        Displays the disconnected icon when currently disconnected.
        """

        self.feed = QLabel()
        self.feed.setFixedSize(1500, 840)

        self.feed.setPixmap(QPixmap("res/not_connected.png"))
        self.feed.setAlignment(Qt.AlignCenter)
        self.bot_layout.addWidget(self.feed)

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """
        Updates the image_label with a new opencv image.
        """

        if self.status == "CONNECTED":
            display_img = cv_img
            qt_img = self.convert_cv_qt(display_img)
            self.feed.setPixmap(qt_img)
            self.feed_thread.grab_frame = True
        else:
            self.feed.setPixmap(QPixmap("res/not_connected.png"))
            self.update()

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

    def display_logs(self):
        """
        Display logs on the right side of the screen, used to debug program.
        """

        logs_w = QWidget()
        logs_l = QVBoxLayout()
        logs_w.setLayout(logs_l)

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
        self.logger.setFixedSize(346, 770)
        self.logger.setReadOnly(True)
        self.logger.setFocusPolicy(Qt.NoFocus)

        self.logger.setAlignment(Qt.AlignJustify)
        self.logger.setText("Welcome to RFES Control Center.")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

        self.bot_layout.addWidget(logs_w)

    def log(self, side, message):
        """
        Logs information onto the Log window along with the time.
        :param side: message source, client/server
        :param message: the message to be logged
        """

        # print(side, message)
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

    def create_label_panel(self):
        """
        Labels of the IP Address and the Port.
        """

        # Inside top left widget, left side
        TL_L_widget = QWidget()
        TL_L_layout = QVBoxLayout()
        TL_L_widget.setLayout(TL_L_layout)

        ip_label = QLabel("IP Address:")
        ip_label.setFont(QFont("sans serif", 15))
        ip_label.setFixedSize(120, 30)
        TL_L_layout.addWidget(ip_label)

        port_label = QLabel("Port:")
        port_label.setFont(QFont("sans serif", 15))
        port_label.setFixedSize(40, 30)
        TL_L_layout.addWidget(port_label)

        self.TL_layout.addWidget(TL_L_widget)

    def create_entry_panel(self):
        """
        The panel for the text entries.
        """

        # Inside top left widget, right side
        TL_R_widget = QWidget()
        TL_R_layout = QVBoxLayout()
        TL_R_widget.setLayout(TL_R_layout)

        self.ip_entry = QLineEdit()
        self.ip_entry.setFixedSize(200, 25)
        self.ip_entry.setPlaceholderText(self.defaultIP)
        self.ip_entry.setText(self.defaultIP)
        self.ip_entry.setFont(QFont("sans serif", 12))
        TL_R_layout.addWidget(self.ip_entry)

        self.port_entry = QLineEdit()
        self.port_entry.setFixedSize(80, 25)
        self.port_entry.setPlaceholderText(self.defaultPort)
        self.port_entry.setText(self.defaultPort)
        self.port_entry.setFont(QFont("sans serif", 12))
        TL_R_layout.addWidget(self.port_entry)
        self.TL_layout.addWidget(TL_R_widget)

    def create_connect_disconnect_panel(self):
        """
        The panel for the connect/disconnect button.
        """

        button_widget = QWidget()
        button_layout = QVBoxLayout()
        button_widget.setLayout(button_layout)

        left_spacer = QSpacerItem(0, 1)
        button_layout.addItem(left_spacer)

        self.c_d_button.setText("Connect")
        self.c_d_button.setFont(QFont("sans serif", 12))
        self.c_d_button.setFixedSize(200, 40)
        self.c_d_button.clicked.connect(self.connect_to_server)
        # click only focus
        self.c_d_button.setFocusPolicy(Qt.ClickFocus)

        button_layout.addWidget(self.c_d_button)

        right_spacer = QSpacerItem(800, 1)
        button_layout.addItem(right_spacer)

        self.TL_layout.addWidget(button_widget)

    def show_status(self):
        """
        Displays the connection status.
        """

        self.status_label = QLabel()
        font = QFont("sans serif", 20)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setFixedSize(220, 100)
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet("color:red")

        self.TR_layout.addWidget(self.status_label)

    def update_status(self):
        """
        Updates the status of the connection.
        """

        if self.status == "DISCONNECTED":
            self.ip_entry.setReadOnly(False)
            self.ip_entry.setDisabled(False)

            self.port_entry.setReadOnly(False)
            self.port_entry.setDisabled(False)
            self.c_d_button.setText("Connect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:red")

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

            self.c_d_button.setText("Disconnect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:green")

            # self.bot_layout.removeWidget(self.feed)
            # self.feed.setParent(None)
            # self.bot_layout.insertWidget(0, self.browser)
            # create the video capture thread


def main():
    """
    Main method.
    """

    myappid = 'rfes-control-center'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
