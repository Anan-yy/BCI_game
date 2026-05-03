"""主菜单 - 游戏启动后的第一个界面"""

from __future__ import annotations

import math
import os
import random

import pygame

from config import (
    BADGE_IMGS,
    IMAGES_DIR,
    INGREDIENT_COLORS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from menu.bci_button import BCIModeButton
from menu.components import Badge, MenuItem
from menu.mode_selector import ModeSelector
from menu.particles import FloatingItem, SteamParticle
from menu.screens.game_settings import GameSettingsScreen


class MainMenu:
    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, title_font: pygame.font.Font) -> None:
        self.screen = screen
        self.font = font
        self.title_font = title_font
        self.clock = pygame.time.Clock()
        self.running = True
        self.result = None
        self.current_mode = "regular"

        self.bg = self._load_bg()
        self.badge = Badge(BADGE_IMGS, SCREEN_WIDTH - 85, 12, size=(80, 80))
        self.floating_items = [
            FloatingItem(SCREEN_WIDTH, SCREEN_HEIGHT, c)
            for c in list(INGREDIENT_COLORS.values()) + [(255, 180, 100)] * 3
        ]
        self.steam_particles = []
        self.steam_spawn_timer = 0

        # ==========================================
        # 按键布局参数
        # ==========================================
        cx = SCREEN_WIDTH // 2 - 400  # 按钮组水平中心：往左偏 100 像素
        cy = SCREEN_HEIGHT // 4  # 屏幕垂直中心
        btn_spacing = 95  # 按钮垂直间距（像素），数值越大按钮间距越大
        start_y = cy + 50 # 按钮 1 坐标：往上偏，数值越大整体越靠下
        # ==========================================

        self.start_btn = MenuItem(
            "开始游戏",
            cx,
            start_y,  # 按钮 1 位置
            title_font,
            (255, 140, 50),
            (255, 170, 80),
            (255, 255, 255),
        )

        self.mode_selector = ModeSelector(
            cx,
            start_y + btn_spacing,  # 按钮 2 位置（按钮 1 下方 + 间距）
            font,
            title_font,
            mode_keys=["regular", "challenge", "creative"],
        )

        self.bci_btn = BCIModeButton("脑机接口", cx, start_y + btn_spacing * 2, font, title_font)  # 按钮 3 位置

        self.settings_btn = MenuItem(
            "游戏设置",
            cx,
            start_y + btn_spacing * 3,  # 按钮 4 位置（按钮 1 下方 + 3倍间距）
            title_font,
            (60, 140, 80),
            (90, 170, 110),
            (255, 255, 255),
        )

        self.btn_cx = cx  # 保存按钮组水平中心，用于标题对齐

        self.title_y = start_y - 150  # 标题 Y 坐标：固定在第一个按钮上方 xx 像素处
        self.title_phase = 0.0

    def _load_bg(self) -> pygame.Surface | None:
        """
        加载背景图片
        :return: 背景图片
        """
        path = os.path.join(IMAGES_DIR, "backgrounds", "菜单页.jpg")
        if os.path.exists(path):
            img = pygame.image.load(path).convert()
            return pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return None

    def run(self) -> tuple[str | None, str]:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.result = "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        self.result = "quit"
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_1:
                        self.running = False
                        self.result = "start"
                    elif event.key == pygame.K_2:
                        self.running = False
                        self.result = "mode"
                    elif event.key == pygame.K_3:
                        self.running = False
                        self.result = "settings"
                else:
                    if self.badge.handle_event(event):
                        pass
                    if self.start_btn.handle_event(event):
                        self.running = False
                        self.result = "start"
                    mode = self.mode_selector.handle_event(event)
                    if mode:
                        self.current_mode = mode
                    if self.bci_btn.handle_event(event):
                        self.running = False
                        self.result = "start"
                        self.current_mode = "bci"
                    if self.settings_btn.handle_event(event):
                        settings_screen = GameSettingsScreen(self.screen, self.font, self.title_font)
                        settings_screen.run()

            self._update(dt)
            self._draw(dt)
            pygame.display.flip()

        return self.result, self.current_mode

    def _update(self, dt: float) -> None:
        self.badge.update(dt)
        self.start_btn.update(dt)
        self.mode_selector.update(dt)
        self.bci_btn.update(dt)
        self.settings_btn.update(dt)

        for item in self.floating_items:
            item.update()

        # 注释：取消背景呼吸缩放效果
        # self.bg_breathe_phase += dt * 0.5
        # self.bg_breathe_scale = 1.0 + math.sin(self.bg_breathe_phase) * 0.008

        self.steam_spawn_timer += dt
        if self.steam_spawn_timer > 0.05:
            self.steam_spawn_timer = 0
            spawn_x = random.uniform(SCREEN_WIDTH * 0.3, SCREEN_WIDTH * 0.7)
            self.steam_particles.append(SteamParticle(int(spawn_x), SCREEN_HEIGHT + 10))
        self.steam_particles = [p for p in self.steam_particles if p.update()]

        self.title_phase += dt * 2

    def _draw(self, dt: float) -> None:
        # 取消背景呼吸缩放效果，直接绘制
        if self.bg:
            self.screen.blit(self.bg, (0, 0))
        else:
            self.screen.fill((255, 240, 220))

        # 增加半透明遮罩层，提升标题和按钮的可读性
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 25))  # 参数说明：(r, g, b, a) 表示 RGBA 颜色
        self.screen.blit(overlay, (0, 0))

        for p in self.steam_particles:
            p.draw(self.screen)

        self.badge.draw(self.screen)

        for item in self.floating_items:
            item.draw(self.screen)

        title_offset = math.sin(self.title_phase) * 8
        title_surf = self.title_font.render("疯狂奶茶杯", True, (255, 220, 150))
        title_shadow = self.title_font.render("疯狂奶茶杯", True, (80, 40, 10))

        tw = title_surf.get_width()
        tx = self.btn_cx - tw // 2  # 标题水平对齐到按钮组
        ty = self.title_y + title_offset - 3
        self.screen.blit(title_shadow, (tx + 3, ty + 3))
        self.screen.blit(title_surf, (tx, ty))

        sub_surf = self.font.render("接住食材 · 制作属于你的美味奶茶", True, (220, 200, 170))
        sw = sub_surf.get_width()
        self.screen.blit(sub_surf, (self.btn_cx - sw // 2, ty + 60))  # 副标题水平对齐到按钮组

        self.start_btn.draw(self.screen)
        self.mode_selector.draw(self.screen)
        self.bci_btn.draw(self.screen)
        self.settings_btn.draw(self.screen)

        hint = self.font.render("ESC 退出", True, (180, 180, 180))
        self.screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 20, SCREEN_HEIGHT - 35))
