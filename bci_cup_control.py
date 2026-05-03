import json
import sys

from PyQt5.QtCore import (
    QByteArray,
    QDataStream,
    QIODevice,
    QObject,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt5.QtNetwork import QAbstractSocket, QTcpSocket
from PyQt5.QtWidgets import *


class HNNKTcpSocketClient(QObject):
    server_connected = pyqtSignal()
    server_disconnected = pyqtSignal()
    recv_from_server = pyqtSignal(QByteArray)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.socket = QTcpSocket(self)
        self.socket.connected.connect(self.on_server_connected)
        self.socket.disconnected.connect(self.on_server_disconnected)
        self.socket.readyRead.connect(self.on_recv_from_server)
        self.recv_buffer = QByteArray()

    def connect_server(self, ip, port):
        self.recv_buffer.clear()
        self.socket.connectToHost(ip, port)

    def close_server(self):
        self.recv_buffer.clear()
        self.socket.disconnectFromHost()

    def send_to_server(self, data):
        if self.socket.state() != QAbstractSocket.ConnectedState:
            return
        payload = QByteArray(data)
        packet = QByteArray()
        stream = QDataStream(packet, QIODevice.WriteOnly)
        stream.setByteOrder(QDataStream.BigEndian)
        stream.writeUInt32(payload.size())
        packet.append(payload)
        self.socket.write(packet)

    @pyqtSlot()
    def on_server_connected(self):
        self.server_connected.emit()

    @pyqtSlot()
    def on_server_disconnected(self):
        self.server_disconnected.emit()

    @pyqtSlot()
    def on_recv_from_server(self):
        self.recv_buffer.append(self.socket.readAll())
        while True:
            if self.recv_buffer.size() < 4:
                return
            stream = QDataStream(self.recv_buffer)
            stream.setByteOrder(QDataStream.BigEndian)
            payload_len = stream.readUInt32()
            total_len = 4 + payload_len
            if self.recv_buffer.size() < total_len:
                return
            payload = self.recv_buffer.mid(4, payload_len)
            self.recv_buffer.remove(0, total_len)
            self.recv_from_server.emit(payload)


class DeadZoneFilter:
    def __init__(self, dead_zone=2.0, smooth_factor=0.3):
        self.dead_zone = dead_zone
        self.smooth_factor = smooth_factor
        self.filtered_value = 0.0
        self.last_valid_value = 0.0

    def filter(self, raw_value):
        if abs(raw_value) < self.dead_zone:
            return self.last_valid_value
        smoothed = self.filtered_value + self.smooth_factor * (
            raw_value - self.filtered_value
        )
        self.filtered_value = smoothed
        self.last_valid_value = smoothed
        return smoothed


class CupController:
    def __init__(self):
        self.yaw_filter = DeadZoneFilter(dead_zone=2.0, smooth_factor=0.3)

    def move_cup(self, yaw_value):
        filtered_yaw = self.yaw_filter.filter(yaw_value)
        print(f"[杯子控制] 原始Yaw: {yaw_value:.2f}°, 滤波后: {filtered_yaw:.2f}°")
        return filtered_yaw


class BCIMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client_socket = HNNKTcpSocketClient()
        self.client_socket.server_connected.connect(self.on_server_connected)
        self.client_socket.server_disconnected.connect(self.on_server_disconnected)
        self.client_socket.recv_from_server.connect(self.on_server_data)

        self.connect_status = False
        self.layout_type = 0
        self.cup_controller = CupController()
        self.init_ui()

    def init_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: white;")
        self.resize(800, 500)

        central_widget = QWidget(self)
        vbox = QVBoxLayout(central_widget)
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)

        self.title_bar = QLabel("BCI 杯子控制 Demo")
        self.title_bar.setStyleSheet(
            "background: #4CAF50; color: white; padding: 10px; font-size: 18px;"
        )
        vbox.addWidget(self.title_bar)

        client_widget = QWidget()
        vbox.addWidget(client_widget)

        connect_widget = QWidget()
        connect_hbox = QHBoxLayout()

        self.server_ip_lineedit = QLineEdit("127.0.0.1")
        self.server_port_lineedit = QLineEdit("8000")

        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.connect_server)
        self.disconnect_button = QPushButton("断开")
        self.disconnect_button.setEnabled(False)
        self.disconnect_button.clicked.connect(self.disconnect_server)

        self.status_label = QLabel("状态: 未连接")
        self.status_label.setAlignment(Qt.AlignCenter)

        connect_hbox.addWidget(QLabel("IP:"))
        connect_hbox.addWidget(self.server_ip_lineedit)
        connect_hbox.addWidget(QLabel("端口:"))
        connect_hbox.addWidget(self.server_port_lineedit)
        connect_hbox.addWidget(self.connect_button)
        connect_hbox.addWidget(self.disconnect_button)
        connect_hbox.addWidget(self.status_label)
        connect_widget.setLayout(connect_hbox)

        content_widget = QFrame()
        content_widget.setObjectName("contentFrame")
        content_widget.setStyleSheet(
            "#contentFrame { border: 2px solid #9EA0A5; border-radius: 4px; }"
        )
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignCenter)

        self.attention_label = QLabel("专注力: --")
        self.attention_label.setStyleSheet(
            "color: black; font-size: 24px; font-weight: bold;"
        )
        content_layout.addWidget(self.attention_label)

        self.yaw_label = QLabel("Yaw: --")
        self.yaw_label.setStyleSheet("color: blue; font-size: 20px;")
        content_layout.addWidget(self.yaw_label)

        self.cup_label = QLabel("杯子状态: 等待数据...")
        self.cup_label.setStyleSheet("color: green; font-size: 18px;")
        content_layout.addWidget(self.cup_label)

        client_box = QVBoxLayout()
        client_box.addWidget(connect_widget, 1)
        client_box.addWidget(content_widget, 4)
        client_widget.setLayout(client_box)

        self.setCentralWidget(central_widget)

    def connect_server(self):
        host = self.server_ip_lineedit.text().strip()
        port = int(self.server_port_lineedit.text().strip())
        self.client_socket.connect_server(host, port)

    def disconnect_server(self):
        self.client_socket.close_server()

    def on_server_connected(self):
        print("[BCI] 已连接到科创平台")
        self.connect_status = True
        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)
        self.status_label.setText("状态: 已连接")

    def on_server_disconnected(self):
        print("[BCI] 与科创平台断开连接")
        self.connect_status = False
        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)
        self.status_label.setText("状态: 已断开")

    def on_server_data(self, data):
        try:
            ipc_json_data = json.loads(data.data().decode("utf-8"))
            msg = ipc_json_data.get("msg", "")

            if msg == "ipc_algorithm_test":
                algorithm_name = ipc_json_data.get("algorithm_name", "")
                result_args = ipc_json_data.get("result_args", {})
                data_content = result_args.get("data", None)

                if algorithm_name == "attention" and data_content is not None:
                    attention_value = int(data_content)
                    print(f"[专注力] 数值: {attention_value}")
                    self.attention_label.setText(f"专注力: {attention_value}")

                elif algorithm_name == "gyroscope" and data_content is not None:
                    if isinstance(data_content, dict):
                        yaw = float(data_content.get("gyroscope_x", 0.0))
                        print(f"[头动] Yaw(偏航): {yaw:.2f}°")
                        self.yaw_label.setText(f"Yaw: {yaw:.2f}°")
                        filtered_yaw = self.cup_controller.move_cup(yaw)
                        self.cup_label.setText(
                            f"杯子状态: 控制中 (Yaw: {filtered_yaw:.2f}°)"
                        )

                elif algorithm_name == "blink":
                    blink_state = data_content
                    print(f"[眨眼] 状态: {blink_state}")

            elif msg == "ipc_user_info":
                self.layout_type = ipc_json_data.get("layout_type", 0)
                if self.layout_type == 1:
                    self.title_bar.setVisible(False)

        except Exception as e:
            print(f"[错误] 解析数据失败: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BCIMainWindow()
    window.show()
    sys.exit(app.exec_())
