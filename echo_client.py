# echo-client.py

import sys
from socket import *
import datetime
from threading import Thread
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

HOST = "localhost"  # The server's hostname or IP address
PORT = 0  # The port used by the server, must be >= 1024

class MainWindow(QWidget):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ip_entry = QLineEdit()
        self.port_entry = QLineEdit()
        self.c_d_button = QPushButton()
        self.socket = None

        self.keys = ['0', '0', '0', '0', '0']

        # default values
        self.defaultIP = "localhost"
        self.defaultPort = "2100"

        self.info = QLabel()
        self.setWindowTitle("RFES Control Center")
        self.setGeometry(50, 50, 320, 200)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.top_widget = QWidget()
        self.top_panel_layout = QHBoxLayout()
        self.top_widget.setLayout(self.top_panel_layout)

        self.TL_widget = QWidget()
        self.TL_layout = QVBoxLayout()
        self.TL_widget.setLayout(self.TL_layout)

        self.TR_widget = QWidget()
        self.TR_layout = QVBoxLayout()
        self.TR_layout.setAlignment(Qt.AlignCenter)
        self.TR_widget.setLayout(self.TR_layout)

        self.top_panel_layout.addWidget(self.TL_widget)
        self.top_panel_layout.addWidget(self.TR_widget)

        self.layout.addWidget(self.top_widget)
        self.status = "DISCONNECTED"

        self.create_ip_panel()
        self.create_port_panel()
        self.create_connect_disconnect_panel()
        self.show_status()

    def server_connection(self):
        while self.status == "CONNECTED":
            self.socket.sendall((''.join(self.keys)).encode('utf-8'))
            print("being sent: " + ''.join(self.keys))


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

    def keyPressEvent(self, event):
        if not event.isAutoRepeat():
            if event.text() == 'w':
                self.keys[0] = '1'
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
            if event.text() == 'a':
                self.keys[1] = '0'
            if event.text() == 's':
                self.keys[2] = '0'
            if event.text() == 'd':
                self.keys[3] = '0'
            if event.text() == ' ':
                self.keys[4] = '0'

    def create_ip_panel(self):
        ip_panel_widget = QWidget()
        ip_panel_layout = QHBoxLayout()
        ip_panel_widget.setLayout(ip_panel_layout)

        ip_label = QLabel("IP Address:")
        ip_panel_layout.addWidget(ip_label)

        self.ip_entry = QLineEdit()
        self.ip_entry.setText(self.defaultIP)
        ip_panel_layout.addWidget(self.ip_entry)

        self.TL_layout.addWidget(ip_panel_widget)



    def create_port_panel(self):
        port_panel_widget = QWidget()
        port_panel_layout = QHBoxLayout()
        port_panel_widget.setLayout(port_panel_layout)

        port_label = QLabel("Port:")
        port_panel_layout.addWidget(port_label)

        self.port_entry = QLineEdit()
        self.port_entry.setText(self.defaultPort)
        port_panel_layout.addWidget(self.port_entry)

        self.TL_layout.addWidget(port_panel_widget)

    def create_connect_disconnect_panel(self):
        c_d_widget = QWidget()
        c_d_layout = QHBoxLayout()
        c_d_widget.setLayout(c_d_layout)

        self.c_d_button.setText("Connect")
        self.c_d_button.clicked.connect(self.connect_to_server)

        c_d_layout.addWidget(self.c_d_button)
        self.TL_layout.addWidget(c_d_widget)

    def show_status(self):
        self.status_label = QLabel()
        font = QFont("sans serif", 12)
        font.setBold(True)
        self.status_label.setFont(font)
        self.info.hide()
        self.status_label.setText(self.status)
        self.status_label.setStyleSheet("color:red")

        self.TR_layout.addWidget(self.info)
        self.TR_layout.addWidget(self.status_label)

    def update_status(self):
        if self.status == "DISCONNECTED":
            self.c_d_button.setText("Connect")
            self.status_label.setText(self.status)
            self.status_label.setStyleSheet("color:red")
        else:
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

