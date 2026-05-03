"""
BCI 脑电数据读取模块
通过 TCP Socket 连接到科创平台，获取专注力和头动数据
"""

import json
import logging
import socket
import struct
import time

from bci.config import load_bci_config
from config import BCI_CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)


class BCIDataReader:
    """
    脑电数据读取器

    功能:
        - 通过 TCP 连接到科创平台获取专注力和头动数据
        - 支持超时检测和数据滤波
        - 支持自定义服务器IP和端口
    """

    def __init__(self, ip=None, port=None):
        bci_config = load_bci_config()
        self.server_ip = ip or bci_config["server_ip"]
        self.server_port = port or bci_config["server_port"]

        self.attention = 50  # 专注力值（0-100），初始值 50
        self.yaw = 0  # 头动偏航角（度），正负表示左右
        self.last_update_time = time.time()  # 上一次成功读取的时间戳
        self.timeout = 0.5  # 超时阈值（秒），500ms 内无新数据视为连接断开

        self.socket = None
        self.connected = False
        self.recv_buffer = b""
        self.last_print_time = 0
        self.print_interval = 2.0

    def connect(self, ip=None, port=None):
        """
        连接BCI设备（科创平台TCP服务器）

        参数:
            ip: 服务器IP地址，默认使用 config.py 中的配置
            port: 服务器端口号，默认使用 config.py 中的配置

        返回:
            bool: 连接是否成功
        """
        if ip:
            self.server_ip = ip
        if port:
            self.server_port = port

        logger.info("[BCI] 尝试连接到 %s:%s...", self.server_ip, self.server_port)

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(BCI_CONNECTION_TIMEOUT)
            self.socket.connect((self.server_ip, self.server_port))
            self.socket.settimeout(0)  # 连接成功后设为非阻塞模式
            self.connected = True
            self.recv_buffer = b""
            self.last_update_time = time.time()
            logger.info("[BCI] 已连接到科创平台")
            return True
        except socket.timeout:
            logger.warning("[BCI] 连接超时（%s秒）", BCI_CONNECTION_TIMEOUT)
            self.connected = False
        except ConnectionRefusedError:
            logger.error(
                "[BCI] 连接被拒绝，请检查科创平台是否已启动（%s:%s）",
                self.server_ip,
                self.server_port,
            )
            self.connected = False
        except Exception as e:
            logger.error("[BCI] 连接失败: %s", e)
            self.connected = False

        return False

    def disconnect(self):
        """断开BCI连接"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.connected = False
        logger.info("[BCI] 已断开连接")

    def _recv_data(self):
        """
        接收TCP数据并解析JSON

        返回:
            dict: 解析后的JSON数据，如果无数据或解析失败返回 None
        """
        if not self.socket or not self.connected:
            return None

        try:
            data = self.socket.recv(4096)
            if not data:
                return None
            self.recv_buffer += data
        except BlockingIOError:
            return None
        except Exception as e:
            logger.error("[BCI] 接收数据失败: %s", e)
            self.connected = False
            return None

        while len(self.recv_buffer) >= 4:
            payload_len = struct.unpack(">I", self.recv_buffer[:4])[0]
            total_len = 4 + payload_len

            if len(self.recv_buffer) < total_len:
                break

            payload = self.recv_buffer[4:total_len]
            self.recv_buffer = self.recv_buffer[total_len:]

            try:
                msg = json.loads(payload.decode("utf-8"))
                return msg
            except json.JSONDecodeError:
                logger.warning("[BCI] JSON解析失败")
                continue

        return None

    def read_data(self, verbose=False):
        """
        读取脑电数据

        参数:
            verbose: 是否打印数据到终端，默认 False

        返回:
            (attention, yaw) 元组，如果设备未连接则返回 (None, None)
                attention: 专注力值（0-100）
                yaw: 头动偏航角（-30 ~ 30）
        """
        if not self.connected:
            return None, None

        msg = self._recv_data()
        if msg is None:
            current_time = time.time()
            if current_time - self.last_update_time > self.timeout:
                self.connected = False
                logger.warning("[BCI] 数据超时，连接可能已断开")
            return self.attention, self.yaw

        try:
            msg_type = msg.get("msg", "")

            if msg_type == "ipc_algorithm_test":
                algorithm_name = msg.get("algorithm_name", "")
                result_args = msg.get("result_args", {})
                data_content = result_args.get("data", None)

                if algorithm_name == "attention" and data_content is not None:
                    self.attention = int(data_content)
                    self.last_update_time = time.time()
                    if (
                        verbose
                        and time.time() - self.last_print_time >= self.print_interval
                    ):
                        logger.debug("[BCI] 专注力: %s", self.attention)
                        self.last_print_time = time.time()

                elif algorithm_name == "gyroscope" and data_content is not None:
                    if isinstance(data_content, dict):
                        self.yaw = float(data_content.get("gyroscope_x", 0.0))
                        self.last_update_time = time.time()
                    if (
                        verbose
                        and time.time() - self.last_print_time >= self.print_interval
                    ):
                        logger.debug("[BCI] Yaw: %.2f", self.yaw)
                        self.last_print_time = time.time()

                elif algorithm_name == "blink":
                    if verbose:
                        logger.debug("[BCI] 眨眼: %s", data_content)

        except Exception as e:
            logger.error("[BCI] 解析数据失败: %s", e)
            return None, None

        return self.attention, self.yaw

    def read_with_timeout(self):
        """
        带超时的数据读取

        返回:
            (attention, yaw) 元组，如果设备未连接或超时则返回 (None, None)
        """
        return self.read_data(verbose=True)
