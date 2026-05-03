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
        self.bg_breathe_phase = 0.0

        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        btn_spacing = 90
        start_y = cy + 20

        self.start_btn = MenuItem(
            "开始游戏",
            cx,
            start_y,
            title_font,
            (255, 140, 50),
            (255, 170, 80),
            (255, 255, 255),
        )

        self.mode_selector = ModeSelector(
            cx,
            start_y + btn_spacing,
            font,
            title_font,
            mode_keys=["regular", "challenge", "creative"],
        )

        self.bci_btn = BCIModeButton("脑机接口", cx, start_y + btn_spacing * 2, font, title_font)

        self.settings_btn = MenuItem(
            "游戏设置",
            cx,
            start_y + btn_spacing * 3,
            title_font,
            (60, 140, 80),
            (90, 170, 110),
            (255, 255, 255),
        )

        self.title_y = 100
        self.title_phase = 0.0
        self.bg_breathe_scale = 1.0

    def _load_bg(self) -> pygame.Surface | None:
        path = os.path.join(IMAGES_DIR, "backgrounds", "奶茶店1.png")
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

        self.bg_breathe_phase += dt * 0.5
        self.bg_breathe_scale = 1.0 + math.sin(self.bg_breathe_phase) * 0.008

        self.steam_spawn_timer += dt
        if self.steam_spawn_timer > 0.05:
            self.steam_spawn_timer = 0
            spawn_x = random.uniform(SCREEN_WIDTH * 0.3, SCREEN_WIDTH * 0.7)
            self.steam_particles.append(SteamParticle(int(spawn_x), SCREEN_HEIGHT + 10))
        self.steam_particles = [p for p in self.steam_particles if p.update()]

        self.title_phase += dt * 2

    def _draw(self, dt: float) -> None:
        if self.bg:
            scale_offset = (SCREEN_WIDTH * self.bg_breathe_scale - SCREEN_WIDTH) // 2
            scaled_bg = pygame.transform.scale(
                self.bg,
                (
                    int(SCREEN_WIDTH * self.bg_breathe_scale),
                    int(SCREEN_HEIGHT * self.bg_breathe_scale),
                ),
            )
            self.screen.blit(scaled_bg, (-scale_offset, -scale_offset))
        else:
            self.screen.fill((255, 240, 220))

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
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
        tx = (SCREEN_WIDTH - tw) // 2
        ty = self.title_y + title_offset - 3
        self.screen.blit(title_shadow, (tx + 3, ty + 3))
        self.screen.blit(title_surf, (tx, ty))

        sub_surf = self.font.render("接住食材 · 制作属于你的美味奶茶", True, (220, 200, 170))
        sw = sub_surf.get_width()
        self.screen.blit(sub_surf, ((SCREEN_WIDTH - sw) // 2, ty + 60))

        self.start_btn.draw(self.screen)
        self.mode_selector.draw(self.screen)
        self.bci_btn.draw(self.screen)
        self.settings_btn.draw(self.screen)

        hint = self.font.render("ESC 退出", True, (180, 180, 180))
        self.screen.blit(hint, (SCREEN_WIDTH - hint.get_width() - 20, SCREEN_HEIGHT - 35))
