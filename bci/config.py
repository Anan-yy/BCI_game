"""BCI 配置管理模块 - 保存和加载 BCI 连接设置"""

import json
import logging
import os

logger = logging.getLogger(__name__)

BCI_CONFIG_FILE = "bci_config.json"
DEFAULT_CONFIG = {
    "server_ip": "127.0.0.1",
    "server_port": 8000,
}


def load_bci_config():
    """
    加载 BCI 配置文件

    返回:
        dict: 包含 server_ip 和 server_port 的配置字典
    """
    if os.path.exists(BCI_CONFIG_FILE):
        try:
            with open(BCI_CONFIG_FILE, encoding="utf-8") as f:
                config = json.load(f)
                return {
                    "server_ip": config.get("server_ip", DEFAULT_CONFIG["server_ip"]),
                    "server_port": config.get(
                        "server_port", DEFAULT_CONFIG["server_port"]
                    ),
                }
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_bci_config(ip, port):
    """
    保存 BCI 配置文件

    参数:
        ip: 服务器IP地址
        port: 服务器端口号
    """
    config = {
        "server_ip": ip,
        "server_port": port,
    }
    try:
        with open(BCI_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("[BCI配置] 保存失败: %s", e)
        return False
