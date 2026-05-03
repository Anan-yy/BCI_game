"""日志配置模块"""

import logging
import os


def setup_logging(level=logging.INFO, log_file=None):
    """配置全局日志

    参数:
        level: 日志级别，默认 INFO
        log_file: 日志文件路径，如果为 None 则只输出到控制台
    """
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.StreamHandler()]

    if log_file:
        os.makedirs(
            os.path.dirname(log_file) if os.path.dirname(log_file) else ".",
            exist_ok=True,
        )
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )


def get_logger(name):
    """获取命名日志器

    参数:
        name: 日志器名称，通常使用 __name__

    返回:
        logging.Logger 对象
    """
    return logging.getLogger(name)
