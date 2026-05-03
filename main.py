"""疯狂奶茶杯 - 游戏主入口
负责初始化 pygame、管理界面跳转（主菜单 -> 模式选择 -> 游戏）
"""

import logging
import os
import sys

import pygame

from config import IMAGES_DIR, SCREEN_HEIGHT, SCREEN_WIDTH
from game.font_utils import load_chinese_font
from game.session import run_game
from menu import GameSettingsScreen, MainMenu
from menu.splash import SplashScreen
from menu.transition import StartTransition
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def show_menu(screen):
    """显示主菜单界面，返回 (result, mode)"""
    font = load_chinese_font(24)
    title_font = load_chinese_font(40)
    menu = MainMenu(screen, font, title_font)
    return menu.run()


def main():
    """游戏主入口，管理界面循环跳转"""
    setup_logging(level=logging.INFO, log_file="game.log")
    logger.info("游戏启动")

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("疯狂奶茶杯 - 第1周")
    icon_path = os.path.join(IMAGES_DIR, "other", "游戏图标.png")
    if os.path.exists(icon_path):
        pygame.display.set_icon(pygame.image.load(icon_path))

    # 播放启动动画
    splash_font = load_chinese_font(110)
    SplashScreen(screen, splash_font).run()

    clock = pygame.time.Clock()

    while True:
        # 1. 显示主菜单（含模式选择）
        result, mode = show_menu(screen)

        if result == "quit":
            break
        elif result == "settings":
            settings_screen = GameSettingsScreen(
                screen, load_chinese_font(24), load_chinese_font(40)
            )
            settings_screen.run()
            continue
        elif result == "start":
            # 2. 播放开始过场动画
            StartTransition(screen).run()
            # 3. 进入主游戏
            game_result = run_game(screen, clock, game_mode=mode)
            if game_result == "quit":
                break
            elif game_result == "menu":
                continue

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
