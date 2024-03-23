# echo-client.py
import traceback
from datetime import datetime
import time
import sys
from socket import *
import multiprocessing
from threading import Thread

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *
import ctypes

import cv2
import numpy as np
import base64

HOST = "172.20.10.3"  # The server's hostname or IP address
# Pi server = 172.20.10.3
PORT = 2100  # The port used by the server, must be >= 1024

client = 0
server = 1


class VideoThreadPiCam(QThread):

    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, parent, status, host, port):
        super().__init__(parent)
        self.connected = status
        self.client_socket = None
        self.host = host
        self.port = port
        self.grab_frame = True

    def run(self):
        BUFF_SIZE = 100000
        addr = (self.host, self.port)
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect(addr)
        while True:
            try:
                packet = self.client_socket.recv(BUFF_SIZE)
                print(len(packet))
                data = base64.b64decode(packet)
                frame = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                self.change_pixmap_signal.emit(frame)
                self.grab_frame = False
                # 11572
                # 20440
                # 11684
                # 17520
                # 14452
                # 20440
                # 11608
                # 20440
                # 11644
            except Exception as e:
                pass
                # print(e)

class WorkerThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, parent, side, message):
        super().__init__(parent)
        self.side = side
        self.message = message

    def run(self):
        self.update_signal.emit(self.side, self.message)


class MainWindow(QWidget):

    def __init__(self):
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
        # corresponds to [W, A, S, D, spacebar, up, down, left, right]
        self.keys = ['0', '0', '0', '0', '0', '0', '0', '0', '0']

        self.display_width = 1500
        self.display_height = 840

        # default values
        self.defaultIP = str(HOST)
        self.defaultPort = str(PORT)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.top_widget = QWidget()
        self.top_panel_layout = QHBoxLayout()
        self.top_widget.setLayout(self.top_panel_layout)

        self.TL_widget = QWidget()
        self.TL_layout = QHBoxLayout()
        self.TL_layout.setAlignment(Qt.AlignLeft)
        self.TL_widget.setLayout(self.TL_layout)

        self.TR_widget = QWidget()
        self.TR_layout = QVBoxLayout()
        self.TR_layout.setAlignment(Qt.AlignRight)
        self.TR_widget.setLayout(self.TR_layout)

        self.top_panel_layout.addWidget(self.TL_widget)
        self.top_panel_layout.addWidget(self.TR_widget)

        self.layout.addWidget(self.top_widget)

        self.bot_widget = QWidget()
        self.bot_layout = QHBoxLayout()
        self.bot_widget.setLayout(self.bot_layout)

        self.layout.addWidget(self.bot_widget)

        self.status = "DISCONNECTED"

        self.create_label_panel()
        self.create_entry_panel()
        self.show_status()
        self.display_web()
        self.display_logs()
        self.create_connect_disconnect_panel()

    def send_commands(self):
        try:
            self.socket.sendall((''.join(self.keys)).encode('utf-8'))

        except:
            self.status = "DISCONNECTED"
            # worker_thread = WorkerThread(self, server, "Connection with server closed.")
            # worker_thread.update_signal.connect(self.log)
            # worker_thread.start()
            # self.log(client, "Connection with server closed.")
            # self.update_status()

    def connect_to_server(self):
        self.c_d_button.clearFocus()
        if self.status == "DISCONNECTED":
            self.log(client, "Connecting to server...")
            self.socket = socket(AF_INET, SOCK_STREAM)
            try:
                self.socket.connect((self.ip_entry.text(), int(self.port_entry.text())))
                self.log(server, self.socket.recv(1024).decode('utf-8'))
            except:
                self.log(client, "Connection with RFES cannot be established. Try again.")
                return
            self.status = "CONNECTED"
            self.update_status()

            self.feed_thread = VideoThreadPiCam(self, self.status, self.ip_entry.text(), int(self.port_entry.text()) + 1)
            # connect its signal to the update_image slot
            self.feed_thread.change_pixmap_signal.connect(self.update_image)
            # start the thread
            self.feed_thread.start()
            print("STARTING THREAD")

            # self.coms_thread = Thread(target=self.server_connection)
            # self.coms_thread.start()

            self.update()

        else:
            self.status = "DISCONNECTED"
            self.log(client, "Connection closed.")
            self.update_status()
            self.socket.close()

    def display_web(self):
        # self.browser = QWebEngineView()
        # self.browser.setFixedSize(1500, 840)
        # self.browser.setUrl(QUrl("http://google.com"))

        # self.no_feed = QLabel()
        # self.no_feed.setFixedSize(1500, 840)
        # self.no_feed.setPixmap(QPixmap("res/not_connected.png"))
        # self.no_feed.setAlignment(Qt.AlignCenter)
        # self.bot_layout.addWidget(self.no_feed)

        self.feed = QLabel()
        self.feed.setFixedSize(1500, 840)
        self.feed.setPixmap(QPixmap("res/not_connected.png"))
        self.feed.setAlignment(Qt.AlignCenter)
        self.bot_layout.addWidget(self.feed)


    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        """Updates the image_label with a new opencv image"""
        display_img = cv_img
        qt_img = self.convert_cv_qt(display_img)
        self.feed.setPixmap(qt_img)
        self.feed_thread.grab_frame = True

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.display_width, self.display_height)        # Qt.KeepAspectRatio
        return QPixmap.fromImage(p)

    def display_logs(self):
        logs_w = QWidget()
        logs_l = QVBoxLayout()
        logs_w.setLayout(logs_l)

        logger_label = QLabel("Logs")
        logger_label.setFont(QFont("sans serif", 12))
        logs_l.addWidget(logger_label)

        self.logger = QTextBrowser(self)
        self.logger.setFixedSize(330, 800)
        self.logger.setReadOnly(True)
        self.logger.setFocusPolicy(Qt.NoFocus)

        self.logger.setAlignment(Qt.AlignJustify)
        self.logger.setText("Welcome to RFES Control Center.")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

        self.bot_layout.addWidget(logs_w)

    def log(self, side, message):
        time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if side == 0:
            self.logger.setText(str(self.logger.toPlainText()) + "\n" + time + " - CLIENT: " + message)
        else:
            self.logger.setText(str(self.logger.toPlainText()) + "\n" + time + " - SERVER: " + message)
        self.logger.verticalScrollBar().setValue(
            self.logger.verticalScrollBar().maximum()
        )

    def keyPressEvent(self, event):
        key = event.key()
        if not event.isAutoRepeat():
            if key == Qt.Key_W:
                self.keys[0] = '1'
                self.log(client, "Moving forward.")
            if key == Qt.Key_A:
                self.keys[1] = '1'
                self.log(client, "Moving left.")
            if key == Qt.Key_S:
                self.keys[2] = '1'
                self.log(client, "Moving back.")
            if key == Qt.Key_D:
                self.keys[3] = '1'
                self.log(client, "Moving right.")
            if key == Qt.Key_Space:
                self.keys[4] = '1'
                self.log(client, "Firing.")
            if key == Qt.Key_Up:
                self.keys[5] = '1'
                self.log(client, "Panning up.")
            if key == Qt.Key_Down:
                self.keys[6] = '1'
                self.log(client, "Panning down.")
            if key == Qt.Key_Left:
                self.keys[7] = '1'
                self.log(client, "Panning left.")
            if key == Qt.Key_Right:
                self.keys[8] = '1'
                self.log(client, "Panning right.")
            self.send_commands()

    def keyReleaseEvent(self, event):
        key = event.key()
        if not event.isAutoRepeat():
            if key == Qt.Key_W:
                self.keys[0] = '0'
                self.log(client, "Stop moving forward.")
            if key == Qt.Key_A:
                self.keys[1] = '0'
                self.log(client, "Stop moving left.")
            if key == Qt.Key_S:
                self.keys[2] = '0'
                self.log(client, "Stop moving back.")
            if key == Qt.Key_D:
                self.keys[3] = '0'
                self.log(client, "Stop moving right.")
            if key == Qt.Key_Space:
                self.keys[4] = '0'
                self.log(client, "Stop firing.")
            if key == Qt.Key_Up:
                self.keys[5] = '0'
                self.log(client, "Stop panning up.")
            if key == Qt.Key_Down:
                self.keys[6] = '0'
                self.log(client, "Stop panning down.")
            if key == Qt.Key_Left:
                self.keys[7] = '0'
                self.log(client, "Stop panning left.")
            if key == Qt.Key_Right:
                self.keys[8] = '0'
                self.log(client, "Stop panning right.")
            self.send_commands()

    def create_label_panel(self):
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
        button_widget = QWidget()
        button_layout = QVBoxLayout()
        button_widget.setLayout(button_layout)
        # button_layout.setAlignment(Qt.AlignLeft)

        left_spacer = QSpacerItem(0, 1)
        button_layout.addItem(left_spacer)

        self.c_d_button.setText("Connect")
        self.c_d_button.setFont(QFont("sans serif", 12))
        self.c_d_button.setFixedSize(200, 40)
        self.c_d_button.clicked.connect(self.connect_to_server)
        button_layout.addWidget(self.c_d_button)

        right_spacer = QSpacerItem(800, 1)
        button_layout.addItem(right_spacer)

        self.TL_layout.addWidget(button_widget)

    def show_status(self):
        self.status_label = QLabel()
        font = QFont("sans serif", 20)
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setFixedSize(220, 100)
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet("color:red")

        self.TR_layout.addWidget(self.status_label)

    def update_status(self):
        if self.status == "DISCONNECTED":
            self.ip_entry.setReadOnly(False)
            self.port_entry.setReadOnly(False)
            self.c_d_button.setText("Connect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:red")

            # GUI update
            # self.bot_layout.removeWidget(self.browser)
            # self.browser.setParent(None)
            # self.bot_layout.insertWidget(0, self.feed)
            self.feed.setPixmap(QPixmap("res/not_connected.png"))
            self.update()

        else:
            self.ip_entry.setReadOnly(True)
            self.port_entry.setReadOnly(True)
            self.c_d_button.setText("Disconnect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:green")

            # self.bot_layout.removeWidget(self.feed)
            # self.feed.setParent(None)
            # self.bot_layout.insertWidget(0, self.browser)
            # create the video capture thread


def main():

    myappid = 'rfes-control-center'  # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

