"""耐心条模块 - 右下角接料耐心指示器"""

from __future__ import annotations

import math
import os

import pygame

from config import (
    CUP_LEVEL_IMGS,
    PATIENCE_BAR_IMG,
    PATIENCE_BAR_SIZE,
)

CHECK_INTERVAL = 3.0
FULL_BAR_DURATION = 60.0


class PatienceBar:
    """耐心条组件，显示接料耐心剩余情况

    逻辑：
        - 每3秒判断一次：这3秒内是否接住过小料
        - 接住过小料：耐心条向右移动（增加）
        - 没接住小料：耐心条向左移动（减少）
        - 移动速度一致：走完整个耐心条需要60秒
    """

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        self.bar_width = PATIENCE_BAR_SIZE[0]
        self.bar_height = PATIENCE_BAR_SIZE[1]
        self.bar_image: pygame.Surface | None = None
        self._load_bar()

        self.cup_icon: pygame.Surface | None = self._load_cup_icon()
        self.cup_icon_size: tuple[int, int] = (60, 60)
        if self.cup_icon:
            self.cup_icon = pygame.transform.scale(self.cup_icon, self.cup_icon_size)

        self.fill = 1.0
        self.speed = 1.0 / FULL_BAR_DURATION
        self.check_timer = 0.0
        self.caught_in_interval = False
        self.direction = -1

        self.tilt_angle = 0.0
        self.tilt_phase = 0.0

    def _load_bar(self) -> None:
        if os.path.exists(PATIENCE_BAR_IMG):
            try:
                img = pygame.image.load(PATIENCE_BAR_IMG).convert_alpha()
                self.bar_image = pygame.transform.scale(img, (self.bar_width, self.bar_height))
                return
            except Exception:
                pass
        self.bar_image = None

    def _load_cup_icon(self) -> pygame.Surface | None:
        for path in CUP_LEVEL_IMGS:
            if os.path.exists(path):
                try:
                    return pygame.image.load(path).convert_alpha()
                except Exception:
                    pass
        return None

    def on_catch(self) -> None:
        """接住食材时标记当前周期内有接住"""
        self.caught_in_interval = True

    def update(self, dt: float) -> None:
        self.tilt_phase += dt * 4
        self.tilt_angle = math.sin(self.tilt_phase) * 10

        self.check_timer += dt
        if self.check_timer >= CHECK_INTERVAL:
            self.check_timer -= CHECK_INTERVAL
            if self.caught_in_interval:
                self.direction = 1
            else:
                self.direction = -1
            self.caught_in_interval = False

        self.fill += self.speed * self.direction * dt
        self.fill = max(0.0, min(1.0, self.fill))

    def draw(self, screen: pygame.Surface) -> None:
        visible_width = int(self.bar_width * self.fill)

        if self.bar_image and visible_width > 0:
            clip_rect = pygame.Rect(0, 0, visible_width, self.bar_height)
            bar_clip = self.bar_image.subsurface(clip_rect)
            screen.blit(bar_clip, (self.x, self.y))

        cup_x = self.x + visible_width - self.cup_icon_size[0] // 2
        cup_y = self.y - self.cup_icon_size[1] // 2 + 7

        if self.cup_icon:
            tilted = pygame.transform.rotate(self.cup_icon, self.tilt_angle)
            tilted_rect = tilted.get_rect(
                center=(
                    cup_x + self.cup_icon_size[0] // 2,
                    cup_y + self.cup_icon_size[1] // 2,
                )
            )
            screen.blit(tilted, tilted_rect.topleft)
