# echo-client.py

import sys
from socket import *

from threading import Thread

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5.QtCore import *
from PyQt5.QtWebEngineWidgets import *

HOST = "localhost"  # The server's hostname or IP address
PORT = 0  # The port used by the server, must be >= 1024


class WorkerThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, parent, message):
        super().__init__(parent)
        self.message = message

    def run(self):
        self.update_signal.emit(self.message)


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

        self.ip_entry = QLineEdit()
        self.port_entry = QLineEdit()
        self.c_d_button = QPushButton()
        self.socket = None

        # corresponds to W, A, S, D, spacebar
        self.keys = ['0', '0', '0', '0', '0']

        # default values
        self.defaultIP = "localhost"
        self.defaultPort = "2100"

        self.info = QLabel()
        self.info.setFont(QFont("sans serif", 12))

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

    def server_connection(self):
        while self.status == "CONNECTED":
            try:
                self.socket.sendall((''.join(self.keys)).encode('utf-8'))
                # worker_thread = WorkerThread(self, )
                # worker_thread.update_signal.connect(self.log)
                # worker_thread.start()
            except:
                self.status = "DISCONNECTED"
                self.update_status()
                break
            # self.log("testt")      # "being sent: " + ''.join(self.keys)


    def connect_to_server(self):
        self.c_d_button.clearFocus()
        if self.status == "DISCONNECTED":
            self.socket = socket(AF_INET, SOCK_STREAM)
            try:
                self.socket.connect((self.ip_entry.text(), int(self.port_entry.text())))
            except:
                self.info.setText("Connection with RFES cannot be established. Try again.")
                self.info.show()
                return
            self.status = "CONNECTED"
            self.update_status()
            thread = Thread(target=self.server_connection)
            thread.start()
        else:
            self.status = "DISCONNECTED"
            self.update_status()
            self.socket.close()

    def display_web(self):
        # browser = QWebEngineView()
        # browser.setFixedSize(1500, 840)
        # browser.setUrl(QUrl("http://google.com"))
        # self.bot_layout.addWidget(browser)
        sample_pic = QLabel()
        sample_pic.setFixedSize(1500, 840)
        sample_pic.setPixmap(QPixmap("samplefeed.jpg"))
        self.bot_layout.addWidget(sample_pic)

    def display_logs(self):
        logs_w = QWidget()
        logs_l = QVBoxLayout()
        logs_w.setLayout(logs_l)

        logger_label = QLabel("Logs")
        logger_label.setFont(QFont("sans serif", 12))
        logs_l.addWidget(logger_label)

        self.logger = QTextEdit()
        self.logger.setFixedSize(330, 800)
        self.logger.setReadOnly(True)

        self.logger.setAlignment(Qt.AlignBottom)
        self.logger.setText("TEST")
        self.logger.setContentsMargins(5, 0, 0, 5)
        logs_l.addWidget(self.logger)

        self.bot_layout.addWidget(logs_w)

    def log(self, message):
        self.logger.setText(str(self.logger.toPlainText()) + "\n" + "CLIENT: " + message)

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            if event.text() == 'w':
                self.keys[0] = '1'
                self.log("Moving forward.")
            if event.text() == 'a':
                self.keys[1] = '1'
            if event.text() == 's':
                self.keys[2] = '1'
            if event.text() == 'd':
                self.keys[3] = '1'
            if event.text() == ' ':
                self.keys[4] = '1'

    def keyReleaseEvent(self, event):
        if not event.isAutoRepeat():
            if event.text() == 'w':
                self.keys[0] = '0'
                self.log("Stopped moving forward.")
            if event.text() == 'a':
                self.keys[1] = '0'
            if event.text() == 's':
                self.keys[2] = '0'
            if event.text() == 'd':
                self.keys[3] = '0'
            if event.text() == ' ':
                self.keys[4] = '0'

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

        self.info.setFixedSize(400, 20)
        self.info.hide()

        self.TR_layout.addWidget(self.info)
        self.TR_layout.addWidget(self.status_label)

    def update_status(self):
        if self.status == "DISCONNECTED":
            self.c_d_button.setText("Connect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:red")
        else:
            self.info.hide()
            self.c_d_button.setText("Disconnect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:green")



def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

