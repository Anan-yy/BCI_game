"""字体加载工具"""

import os

import pygame

from config import ASSETS_DIR


def load_chinese_font(size=36):
    """
    加载支持中文的字体

    参数:
        size: 字体大小（像素），默认 36

    返回:
        pygame.font.Font 对象
    """
    project_font = os.path.join(ASSETS_DIR, "fonts", "ZCOOLKuaiLe-Regular.ttf")
    if os.path.exists(project_font):
        try:
            return pygame.font.Font(project_font, size)
        except (pygame.error, OSError):
            pass

    try:
        return pygame.font.SysFont("simhei", size)
    except (pygame.error, OSError):
        pass

    return pygame.font.Font(pygame.font.get_default_font(), size)
