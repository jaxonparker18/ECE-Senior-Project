import os
from datetime import datetime
import sys
from socket import *
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
import numpy as np
import base64
import time
import struct
from inference.models.utils import get_roboflow_model
import platform

print(platform.version())
# GLOBAL VARIABLES
HOST = "10.42.0.1"
PORT = 2100  # The port used by the server, must be >= 1024

# constants
CLIENT = 0
SERVER = 1

ON = '1'
OFF = '0'
DC = 'x'

# corresponds to [W, A, S, D, spacebar, up, down, left, right, m_y, m_x, misc]
W_INDEX = 0
A_INDEX = 1
S_INDEX = 2
D_INDEX = 3
SB_INDEX = 4
UP_INDEX = 5
DOWN_INDEX = 6
LEFT_INDEX = 7
RIGHT_INDEX = 8
M_Y_INDEX = 9
M_X_INDEX = 10
MISC1_INDEX = 11
MISC2_INDEX = 12

IDLE      = [DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC,  DC]
OFF_KEYS  = [OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF]

FEED_WIDTH = 0
FEED_HEIGHT = 0

CENTER_X = 0
CENTER_Y = 0

is_auto_detecting = False
is_tracking = False
target_x = 0
target_y = 0
target_width = 0
target_height = 0

# thread stop flags
flag_video_stop = threading.Event()
flag_recv_stop = threading.Event()
flag_script_stop = threading.Event()
flag_script_stop.set()  # so that text is not displayed on the screen
flag_scan_stop = threading.Event()


# SHORTCUT BINDS
TOGGLE_OPEN_WIN = "Ctrl+O"
TOGGLE_LOG_WIN = "Ctrl+L"
TOGGLE_SCRIPT_WIN = "Ctrl+,"
SAVE = "Ctrl+S"


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

        self.main_window = parent
        super().__init__(self.main_window)
        self.connected = status
        self.client_socket = None
        self.host = host
        self.port = port
        self.grab_frame = True
        self.x = 0
        self.frame_threshold = 5   # frames it takes to lock on
        self.frame_counter = 0      # counter
        self.track_loss_threshold = 5   # frames it takes to re-detect
        self.tracker = None
        self.scan_thread = None
        self.auto_scan = True


    def run(self):
        """
        Runs the thread by connecting to the TCP socket receiving frames in bytes and decoding it
        using cv2, then displaying it onto the window.
        """
        global is_auto_detecting, is_tracking
        global target_x, target_y, target_width, target_height
        global FEED_WIDTH, FEED_HEIGHT, CENTER_X, CENTER_Y
        BUFF_SIZE = 65536
        addr = (self.host, self.port)
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect(addr)
        buffer = b''
        # get Roboflow face model
        model_name = "deteksiasapdanapi"  # FIRE
        model_version = "4"
        api_key = "NHxBSfWHlHDOQC07yyLm"
        model = get_roboflow_model(
            model_id="{}/{}".format(model_name, model_version),
            # Replace ROBOFLOW_API_KEY with your Roboflow API Key
            api_key=api_key
        )

        # circle attr
        radius = 3
        thickness = -1
        color = (255, 0, 0)
        while not flag_video_stop.is_set():
            try:
                packet = self.client_socket.recv(BUFF_SIZE)
                buffer += packet

                while b'\0' in buffer:
                    # start = time.time()
                    message, buffer = buffer.split(b'\0', 1)
                    data = base64.b64decode(message)
                    frame = np.frombuffer(data, dtype=np.uint8)
                    frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

                    FEED_WIDTH = frame.shape[1]
                    FEED_HEIGHT = frame.shape[0]

                    CENTER_X = FEED_WIDTH // 2
                    CENTER_Y = FEED_WIDTH // 2

                    # OBJ DETECT ROBOFLOW
                    if is_auto_detecting and not is_tracking:
                        # prev_keys = OFF_KEYS.copy()
                        # self.main_window.keys = OFF_KEYS.copy()
                        # if prev_keys != self.main_window.keys:
                        #     self.main_window.send_commands()
                        results = model.infer(image=frame,
                                              confidence=0.5,
                                              iou_threshold=0.5)
                        if self.scan_thread:
                            print(self.scan_thread.is_alive())
                        if self.auto_scan and (not self.scan_thread or not self.scan_thread.is_alive()):
                            self.scan_thread = threading.Thread(target=self.scan_for_target, args=())
                            self.scan_thread.start()
                            flag_scan_stop.clear()

                        # Plot image with face bounding box (using opencv)
                        if results[0].predictions:
                            prediction = results[0].predictions[0]
                            # class_name = prediction.class_name
                            # confidence = prediction.confidence
                            # print(prediction)
                            # print(class_name)

                            x_center = int(prediction.x)
                            y_center = int(prediction.y)
                            width = int(prediction.width)
                            height = int(prediction.height)

                            # Calculate top-left and bottom-right corners from center, width, and height
                            x0 = x_center - width // 2
                            y0 = y_center - height // 2
                            x1 = x_center + width // 2
                            y1 = y_center + height // 2
                            cv2.rectangle(frame, (x0, y0), (x1, y1), (255, 255, 0), 5)

                            # draw circle in the center of bounding box
                            cv2.circle(frame, (x_center, y_center), radius, color, thickness)

                            target_x = x_center
                            target_y = y_center
                            target_width = width
                            target_height = height

                            cv2.putText(frame, f"ID: Fire {self.frame_counter}", (x0, y0 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
                            self.frame_counter += 1
                            if self.frame_counter >= self.frame_threshold:
                                # object tracking
                                self.tracker = cv2.legacy.TrackerMedianFlow_create()    # cv2.legacy.TrackerMOSSE_create()
                                self.tracker.init(frame, (x0, y0, width, height))
                                is_auto_detecting = False
                                is_tracking = True
                                self.frame_counter = 0
                                flag_scan_stop.set()    # stop scanning
                                # self.main_window.log(CLIENT, "Switching to object tracking...")
                        else:
                            self.frame_counter = 0

                    # Object Tracking
                    if is_tracking and not is_auto_detecting:
                        # update the tracker with the new frame from ID
                        success, bbox = self.tracker.update(frame)

                        # If tracking was successful, draw the bounding box around the object
                        if success:
                            self.frame_counter = 0
                            x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

                            # update target coordinates
                            target_x = x
                            target_y = y
                            target_width = w
                            target_height = h
                            print(w, h)
                            target_dist = self.calculate_target_distance(w, h)
                            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)    # bounding box
                            cv2.putText(frame, f"OT: Tracking Fire (~{target_dist} in.)",
                                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
                            if not self.update_rfes_x(x + (w // 2), y + (h // 2)): # update z if x is perfectly lined up
                                self.update_rfes_z(target_dist)

                        else:
                            cv2.putText(frame, f"OT: Re-detecting in... {self.frame_counter}",
                                        (FEED_WIDTH // 2 - 200, 100),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 2)
                            if self.frame_counter < self.track_loss_threshold:
                                self.frame_counter += 1
                            else:
                                # If tracking fails, display a message
                                # self.main_window.log(CLIENT, "Fire is no longer detected.")
                                is_tracking = False
                                is_auto_detecting = True
                                self.frame_counter = 0
                                self.main_window.keys = OFF_KEYS.copy()
                                self.main_window.send_commands()

                    # draw dot in center video feed
                    cv2.circle(frame, (frame.shape[1] // 2, frame.shape[0] // 2), radius, (0, 105, 255), thickness)  
                    self.change_pixmap_signal.emit(frame)

                    # FPS CHECK
                    # stop = time.time()
                    # print(str(stop-start), "ms")

            except Exception as e:
                print(e)
        self.client_socket.close()

    def scan_for_target(self):
        print("scan thread")
        while not flag_scan_stop.is_set():
            print("in whileloop")
            # continue
            self.main_window.keys = OFF_KEYS.copy()
            self.main_window.keys[A_INDEX] = ON
            self.main_window.keys[MISC2_INDEX] = 's'
            self.main_window.send_commands()
            time.sleep(1)
            self.main_window.keys = OFF_KEYS.copy()
            self.main_window.send_commands()
            time.sleep(3)
        self.main_window.keys[MISC2_INDEX] = DC

    def update_rfes_x(self, fire_center_x, fire_center_y):
        """
        Returns True if RFES needs adjustment, false otherwise. This method
        also sends instructions to RFES on where to adjust.
        :param fire_center_x:
        :param fire_center_y:
        :return:
        """

        global CENTER_X, CENTER_Y
        threshold = 200
        prev_keys = self.main_window.keys.copy()
        move_left = False
        move_right = False

        dx = fire_center_x - CENTER_X
        dy = fire_center_y - CENTER_Y
        if abs(dx) >= threshold:
            if dx > 0:
                move_right = True
            else:
                move_left = True

        if abs(dy) >= threshold:
            if dy > 0:
                pass
                # move servo down
            else:
                pass
                #move servo up

        self.main_window.keys = OFF_KEYS.copy()
        if move_left:    
            self.main_window.keys[A_INDEX] = ON
            self.main_window.keys[MISC2_INDEX] = 't'
            if prev_keys != self.main_window.keys:
                self.main_window.send_commands()
            return True
        elif move_right:
            self.main_window.keys[D_INDEX] = ON
            self.main_window.keys[MISC2_INDEX] = 't'
            if prev_keys != self.main_window.keys:
                self.main_window.send_commands()
            return True
        else:
            self.main_window.keys[MISC2_INDEX] = DC
            if prev_keys != self.main_window.keys:
                self.main_window.send_commands()
            return False
            # print(f"LEFT:{move_left}, RIGHT:{move_right}")
            # print(f"{self.main_window.keys}")
        # self.main_window.log(CLIENT, f"LEFT:{move_left}, RIGHT:{move_right}")
        # self.main_window.log(CLIENT, f"{self.main_window.keys}")

    def update_rfes_z(self, target_dist):
        STOP_DIST = 20
        prev_keys = self.main_window.keys.copy()
        self.main_window.keys = OFF_KEYS.copy()
        if target_dist == "40+" or int(target_dist) >= STOP_DIST:
            self.main_window.keys = OFF_KEYS.copy()
            self.main_window.keys[W_INDEX] = ON
            self.main_window.keys[MISC2_INDEX] = 't'
        else:
            self.main_window.keys[MISC2_INDEX] = DC

        if prev_keys != self.main_window.keys:
            self.main_window.send_commands()
            # print("moving forward!")

    @staticmethod
    def calculate_target_distance(width, height):
        area = width * height
        # 280 218 = 40 ft
        # 325 254 = 35 ft
        # 384 315 = 30 ft
        # 460 420 = 25 ft
        # 554 515 = 20 ft
        # 757 692 = 15 ft
        if area >= (757 * 692):
            return "15"
        elif area >= (554 * 515):
            return "20"
        elif area >= (460 * 520):
            return "25"
        elif area >= (384 * 315):
            return "30"
        elif area >= (325 * 254):
            return "35"
        elif area >= (280 * 218):
            return "40"
        else:
            return "40+"

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
        self.height = 410
        self.modified = False
        self.curr_file = "Untitled"
        self.execute_script_thread = None

        # self.setGeometry(main_window.screen.width() - 418, main_window.screen.height() - 425, 400, 300) # hard code
        self.setGeometry(log_window.geometry().topRight().x() - self.width + 23,    # 23 is offset
                         log_window.geometry().topLeft().y() + log_window.geometry().height() + 115,
                         self.width,
                         self.height)
        self.setMinimumSize(self.width, self.height)
        self.setWindowTitle("Script Editor")

        self.shortcut = QShortcut(QKeySequence(TOGGLE_SCRIPT_WIN), self)
        self.shortcut.activated.connect(self.toggle_script_window)

        self.shortcut = QShortcut(QKeySequence(TOGGLE_LOG_WIN), self)
        self.shortcut.activated.connect(self.toggle_log_window)

        self.shortcut = QShortcut(QKeySequence(SAVE), self)
        self.shortcut.activated.connect(self.quick_save)

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
            "WHERE x IS THE DISTANCE IN FEET \n"
            "left(d)\n"
            "right(d)\n"
            "WHERE d IS THE DEGREES \n"
            "aim_up(s)\n"
            "aim_down(s)\n"
            "aim_left(s)\n"
            "aim_right(s)\n"
            "AND s IS THE DEGREE OF THE TURN \n"
            "\n"
            "EXAMPLE:\n"
            "forward(10) // where 10 is the distance in feet \n"
            "\n"
            "FOR AIMING COMMANDS: \n"
            "aim_up(90) // where 90 is the angle to turn \n"
            "\n"
            "FOR LOOPS: \n"
            "for(n) // where n is the number of loops and end that closes the \n"
            "loop block. For an infinite loop, n = -1. \n"
            "EXAMPLE: \n"
            "for(3) // loops three times \n"
            "forward(3) \n"
            "left(1) \n"
            "end \n")
        self.textBox.textChanged.connect(self.on_text_changed)
        self.submitButton = QPushButton("Push to submit and run code.")
        self.submitButton.clicked.connect(self.on_push_script)
        layout.addWidget(self.textBox)
        layout.addWidget(self.submitButton)
        self.setLayout(layout)
        layout.setMenuBar(menu)

    def quick_save(self):
        try:
            if self.curr_file == "Untitled" or self.curr_file == "":
                self.on_save_script()
            else:
                with open(self.curr_file, 'w') as file:
                    file.write(self.textBox.toPlainText())
                self.on_save()
        except Exception as e:
            self.main_window.log(CLIENT, "Quick save error: " + str(e))

    def on_save(self):
        self.modified = False
        self.setWindowTitle(f"Script Editor - {os.path.splitext(os.path.basename(self.curr_file))[0]}")
        self.modified = False
        self.submitButton.setEnabled(True)

    def on_text_changed(self):
        self.setWindowTitle(f"Script Editor - *{os.path.splitext(os.path.basename(self.curr_file))[0]}")
        self.modified = True
        self.submitButton.setDisabled(True)

    def on_open_script(self):
        # BROWSE FILES AND PRINT CONTENT OF FILE
        try:
            file = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
            self.curr_file = file[0]
            content = open(self.curr_file).read()
            self.textBox.setText(content)
            self.on_save()
        except Exception as e:
            self.main_window.log(CLIENT, "Open error: " + str(e))

    def on_save_script(self):
        try:
            file = QFileDialog.getSaveFileName(self, "Save File", "New_Script", "Text Files (*.txt)")
            self.curr_file = file[0]
            with open(self.curr_file, 'w') as file:
                file.write(self.textBox.toPlainText())
            self.on_save()
        except Exception as e:
            self.main_window.log(CLIENT, "Save error: " + str(e))

    def on_push_script(self):
        self.main_window.log(CLIENT, f"Executing script: {os.path.splitext(os.path.basename(self.curr_file))[0]}")
        self.execute_script_thread = threading.Thread(target=self.main_window.execute_instructions, args=(self.curr_file,),
                                                      daemon=True)  # exit as soon as main thread is done
        self.execute_script_thread.start()
        flag_script_stop.clear()
        self.submitButton.setText("Stop script")
        self.submitButton.clicked.connect(self.stop_script)

    def stop_script(self):
        flag_script_stop.set()
        self.submitButton.setText("Push to submit and run code.")
        self.submitButton.clicked.connect(self.on_push_script)

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
        self.setGeometry(main_window.screen.width() - 335, main_window.screen.height() - 970, self.width, self.height)
        self.shortcut = QShortcut(QKeySequence(TOGGLE_LOG_WIN), self)
        self.shortcut.activated.connect(self.toggle_log_window)

        self.shortcut = QShortcut(QKeySequence(TOGGLE_SCRIPT_WIN), self)
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
        with self.main_window.log_lock:
            curr_time = datetime.now().strftime("%H:%M:%S")
            curr_text = str(self.logger.toPlainText())
            if side == 0:
                self.logger.setText(curr_text + ("\n" if curr_text != "" else "") + curr_time + " - CLIENT: " + message)
            else:
                self.logger.setText(curr_text + (
                    "\n" if self.logger.toPlainText() != "" else "") + curr_time + " - SERVER: " + message)
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

        self.ip_entry = None
        self.port_entry = None
        self.connect_button = None
        self.status_label = None
        self.feed = None

        self.socket = None
        self.nozzle_x = 0
        self.nozzle_y = 0

        self.pi_battery = "0.00%"
        self.cpu_temp = "0" + chr(176) + "C"

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

        self.main_battery_bg = QPixmap("res/main_battery_status.png").scaled(100, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pi_battery_bg = QPixmap("res/pi_battery_status.png").scaled(100, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pi_temperature_bg = QPixmap("res/pi_temperature_status.png").scaled(100, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.feed_thread = None
        self.coms_thread = None
        self.recv_thread = None
        self.run_instr_thread = None

        # locks
        self.log_lock = threading.RLock()

        self.defaultIP = str(HOST)
        self.defaultPort = str(PORT)
        self.status = "DISCONNECTED"

        self.keys = IDLE.copy()

        # mouse track
        self.is_tracking_mouse = False
        self.left_screen = 20
        self.right_screen = 1520
        self.top_screen = 185
        self.bot_screen = 1023

        # servo track
        self.MAX_X = 0
        self.MIN_X = 0
        self.MAX_Y = 0
        self.MIN_Y = 0
        self.curr_servo_x = 0
        self.curr_servo_y = 0

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
        open_script_action.setShortcut(TOGGLE_OPEN_WIN)

        # QAction for write script.
        open_write_script_action = QAction(QIcon("controller.png"), "Write Script", self)
        open_write_script_action.setStatusTip("Opens field to write custom RFES language script.")
        open_write_script_action.triggered.connect(self.on_write_script)
        open_write_script_action.setShortcut(TOGGLE_SCRIPT_WIN)

        # QAction for logger.
        open_logger_action = QAction(QIcon("controller.png"), "Open Log", self)
        open_logger_action.setStatusTip("Opens logger to see updated information.")
        open_logger_action.triggered.connect(self.on_logger)
        open_logger_action.setShortcut(TOGGLE_LOG_WIN)

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

    # def auto_target(self):

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
            self.keys[M_Y_INDEX] = str(round(pwm_y_value, 2))
            self.keys[M_X_INDEX] = str(round(pwm_x_value, 2))
            self.keys[MISC1_INDEX] = 'm'
            self.send_commands()

    def keyPressEvent(self, event):
        """
        Listens for any key pressed events.
        :param event: the type of event that occurs
        """
        global is_auto_detecting, is_tracking

        key = event.key()

        if key == Qt.Key_P:   # for debugging purposes
            self.run_instructions()

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
                self.keys[0] = ON
                self.keys[MISC1_INDEX] = 'k'
            if key == Qt.Key_A:
                self.keys[1] = ON
            if key == Qt.Key_S:
                self.keys[2] = ON
            if key == Qt.Key_D:
                self.keys[3] = ON
            if key == Qt.Key_Space:
                self.keys[4] = ON
            if key == Qt.Key_Up:
                self.keys[5] = ON
            if key == Qt.Key_Down:
                self.keys[6] = ON
            if key == Qt.Key_Left:
                self.keys[7] = ON
            if key == Qt.Key_Right:
                self.keys[8] = ON
            if key == Qt.Key_I:
                if not is_auto_detecting and not is_tracking:
                    self.keys = OFF_KEYS.copy()
                    is_auto_detecting = True
                    is_tracking = False
                    flag_scan_stop.clear()
                else:
                    self.keys = OFF_KEYS.copy()
                    is_auto_detecting = False
                    is_tracking = False
                    flag_scan_stop.set()

            self.keys[MISC1_INDEX] = 'k'
            self.keys[MISC2_INDEX] = OFF     # because this is not in tracking mode
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
                self.keys[W_INDEX] = OFF
            if key == Qt.Key_A:
                self.keys[A_INDEX] = OFF
            if key == Qt.Key_S:
                self.keys[S_INDEX] = OFF
            if key == Qt.Key_D:
                self.keys[D_INDEX] = OFF
            if key == Qt.Key_Space:
                self.keys[SB_INDEX] = OFF
            if key == Qt.Key_Up:
                self.keys[UP_INDEX] = OFF
            if key == Qt.Key_Down:
                self.keys[DOWN_INDEX] = OFF
            if key == Qt.Key_Left:
                self.keys[LEFT_INDEX] = OFF
            if key == Qt.Key_Right:
                self.keys[RIGHT_INDEX] = OFF
            self.keys[MISC1_INDEX] = 'k'
            self.keys[MISC2_INDEX] = OFF  # because this is not in tracking mode
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
                elif data.startswith("/PIB"):
                    self.pi_battery = data[4:]
                elif data.startswith("/CT"):
                    self.cpu_temp = data[3:] + chr(176) + "C"
                elif data.startswith("/X"):
                    pwm = float(data[2:])
                    if (self.MAX_X - self.MIN_X) != 0:
                        self.curr_servo_x = round(((pwm  - self.MIN_X) / (self.MAX_X - self.MIN_X)) * 100)
                elif data.startswith("/Y"):
                    pwm = float(data[2:])
                    if (self.MAX_Y - self.MIN_Y) != 0:
                        self.curr_servo_y = round(((pwm - self.MIN_Y) / (self.MAX_Y - self.MIN_Y)) * 100)
                elif data.startswith("/MM"):
                    data = data[3:].split(",")
                    print(data)
                    self.MAX_X = float(data[0])
                    self.MIN_X = float(data[1])
                    self.MAX_Y = float(data[2])
                    self.MIN_Y = float(data[3])
                else:
                    recv_thread = LoggerThread(self, SERVER, data)
                    recv_thread.update_signal.connect(self.log)
                    recv_thread.start()
            except Exception as e:
                print("server closed: " + str(e))
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
            flag_video_stop.clear()  # resets flag
            self.feed_thread = VideoThreadPiCam(self, self.status, self.ip_entry.text(), int(
                self.port_entry.text()) + 1)
            # connect its signal to the update_image slot
            self.feed_thread.change_pixmap_signal.connect(self.update_image)
            # start the thread
            self.feed_thread.start()
            self.update()

        else:
            self.keys = OFF_KEYS.copy()
            self.send_commands()
            self.status = "DISCONNECTED"
            self.log(CLIENT, "Connection closed.")
            self.update_status()
            self.socket.close()

            # disable all threads
            flag_video_stop.set()
            flag_recv_stop.set()
            flag_script_stop.set()

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """
        Updates the image_label with a new opencv image.
        """

        if self.status == "CONNECTED":
            qt_img = self.convert_cv_qt(cv_img)

            # overlay water level
            self.update_water_indicator()
            water_level = self.curr_wl.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.overlay_pixmap(qt_img, water_level, self.display_width - 330, 25)

            # overlay battery_level img
            self.overlay_pixmap(qt_img, self.pi_battery_bg, self.display_width - 130, 70)

            # overlay battery level text
            battery_level = self.create_pixmap_from_text(f"{self.pi_battery}%", font_size=12)
            self.overlay_pixmap(qt_img, battery_level, self.display_width - 338, 80)

            # overlay cpu temp
            self.overlay_pixmap(qt_img, self.pi_temperature_bg, self.display_width - 130, 110)

            # overlay cpu temp text
            cpu_temp = self.create_pixmap_from_text(f"{self.cpu_temp}", font_size=12)
            self.overlay_pixmap(qt_img, cpu_temp, self.display_width - 335, 120)

            # overlay Script Running text
            if not flag_script_stop.is_set():
                script_display = self.create_pixmap_from_text(f"Script running...", color=QColor("green"))
                self.overlay_pixmap(qt_img, script_display, -70, 5)

            # overlay curr servo x
            curr_x = self.create_pixmap_from_text(f"x: {self.curr_servo_x}", font_size=12)
            self.overlay_pixmap(qt_img, curr_x, -70, 50)

            # overlay curr servo y
            curr_x = self.create_pixmap_from_text(f"y: {self.curr_servo_y}", font_size=12)
            self.overlay_pixmap(qt_img, curr_x, -70, 100)

            self.feed.setPixmap(qt_img)
            self.feed_thread.grab_frame = True
            global target_x
            global target_y
            # print(f"x: {target_x}")
            # print(f"y: {target_y}")
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
                self.curr_wl = self.wl_down_four
                if self.water_level[1] == "1":
                    self.curr_wl = self.wl_down_three
                    if self.water_level[2] == "1":
                        self.curr_wl = self.wl_down_two
                        if self.water_level[3] == "1":
                            self.curr_wl = self.wl_down_one
                            if self.water_level[4] == "1":
                                self.curr_wl = self.wl_full

    @staticmethod
    def create_pixmap_from_text(text, font_name="Arial", font_size=20, color=QColor("black"), width=300,
                                height=100):

        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)

        font = QFont(font_name, font_size)
        painter.setFont(font)
        painter.setPen(color)

        painter.drawText(pixmap.rect(), Qt.AlignRight, text)

        painter.end()
        return pixmap

    @staticmethod
    def overlay_pixmap(base_pixmap, overlay_pixmap, x=0, y=0):
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
        self.run_instr_thread = threading.Thread(target=self.execute_instructions, args=(instructions_path,),
                                                 daemon=True)   # exit as soon as main thread is done
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
        flag_script_stop.clear()
        instructions = Instructions_Reader.path_to_instructions(instructions_path)  # "["forward(10)", "left(90)", ...]"
        for instruction in instructions:    # loops through all instructions
            if flag_script_stop.is_set():   # stops any ongoing commands
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
                i = 0
                print(instructions_to_loop)
                while i < loop and not flag_script_stop.is_set():
                    for ins in instructions_to_loop:

                        if flag_script_stop.is_set():   # stop thread
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
        self.script_window.stop_script()

    def send_script_instructions(self, command, value, delay_between_commands):
        self.keys = OFF_KEYS.copy()
        self.keys[Instructions_Reader.COMMANDS_STRING[command]] = ON
        self.send_commands()
        # print(f"keys sent: {self.keys}")
        time.sleep(self.convert_speed_to_time(command, value))  # execute command for a certain duration
        self.keys = OFF_KEYS.copy()
        self.send_commands()
        time.sleep(delay_between_commands)

    @staticmethod
    def convert_speed_to_time(command, value):
        """
        Converts the speed of a command to the desired time it takes to travel.
        :param command: the command executed
        :param value: value of command
        :return: the time needed
        """
        # CALIBRATION
        FORWARD_ONE_SECOND = 9.65  # inches
        BACKWARD_ONE_SECOND = 10.1  # inches
        degrees_tested = 90
        LEFT_90 = 0.72      # seconds
        RIGHT_90 = 0.756    # seconds
        if command in ["forward", "backward"]:
            speed_ips = 0
            if command == "forward":
                speed_ips = FORWARD_ONE_SECOND
            elif command == "backward":
                speed_ips = BACKWARD_ONE_SECOND
            feet_per_second = speed_ips/12
            time_per_foot = 1/feet_per_second
            return value * time_per_foot
        elif command in ["left", "right"]:
            # value will store the degrees
            time_for_90 = 0
            if command == "left":
                time_for_90 = LEFT_90
            elif command == "right":
                time_for_90 = RIGHT_90
            t_per_deg = time_for_90 / degrees_tested
            return value * t_per_deg
        elif command in ["aim_left", "aim_right", "aim_up", "aim_down"]:
            # if it's aiming, turn value to degrees
            # convert value to angle, so use value to see how long it takes to turn a certain angle
            return value    # not implemented yet
        else: # spray
            return value

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
            self.script_window.on_open_script()
            self.on_write_script()
            # filename = QFileDialog.getOpenFileName(self, "Open File", "", "Text Files (*.txt)")
            # content = open(filename[0]).read()
            # self.script_window.show()
            # self.script_window.textBox.clear()
            # self.script_window.textBox.setText(content)
            # self.script_window.curr_file = filename
            # self.script_window.setWindowTitle(f"Script Editor - {os.path.splitext(os.path.basename(filename[0]))[0]}")

        except Exception as e:
            self.log(CLIENT, "Please select a valid file.")

    def on_write_script(self):
        self.script_window.show()

    def toggle_write_script(self):
        if self.script_window.isVisible():
            self.script_window.hide()
        else:
            self.script_window.show()

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
    my_app_id = 'rfes-control-center'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
