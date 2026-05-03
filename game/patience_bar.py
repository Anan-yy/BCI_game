"""耐心条模块 - 右下角接料耐心指示器"""

import math
import os

import pygame

from config import (
    CUP_LEVEL_IMGS,
    PATIENCE_BAR_IMG,
    PATIENCE_BAR_SIZE,
    PATIENCE_BAR_TIMEOUT,
)


class PatienceBar:
    """耐心条组件，显示接料耐心剩余情况"""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.bar_width = PATIENCE_BAR_SIZE[0]
        self.bar_height = PATIENCE_BAR_SIZE[1]
        self.bar_image = None
        self._load_bar()

        self.cup_icon = self._load_cup_icon()
        self.cup_icon_size = (60, 60)
        if self.cup_icon:
            self.cup_icon = pygame.transform.scale(self.cup_icon, self.cup_icon_size)

        self.fill = 1.0
        self.shrink_speed = 1.0 / PATIENCE_BAR_TIMEOUT
        self.grow_speed = self.shrink_speed
        self.is_growing = False
        self.grow_timer = 0.0

        self.tilt_angle = 0.0
        self.tilt_phase = 0.0

    def _load_bar(self):
        if os.path.exists(PATIENCE_BAR_IMG):
            try:
                img = pygame.image.load(PATIENCE_BAR_IMG).convert_alpha()
                self.bar_image = pygame.transform.scale(
                    img, (self.bar_width, self.bar_height)
                )
                return
            except Exception:
                pass
        self.bar_image = None

    def _load_cup_icon(self):
        for path in CUP_LEVEL_IMGS:
            if os.path.exists(path):
                try:
                    return pygame.image.load(path).convert_alpha()
                except Exception:
                    pass
        return None

    def on_catch(self):
        self.is_growing = True
        self.grow_timer = PATIENCE_BAR_TIMEOUT

    def update(self, dt):
        self.tilt_phase += dt * 4
        self.tilt_angle = math.sin(self.tilt_phase) * 10

        if self.is_growing:
            self.grow_timer -= dt
            self.fill += self.grow_speed * dt
            if self.fill >= 1.0:
                self.fill = 1.0
            if self.grow_timer <= 0:
                self.is_growing = False
        else:
            self.fill -= self.shrink_speed * dt
            if self.fill < 0:
                self.fill = 0

    def draw(self, screen):
        visible_width = int(self.bar_width * self.fill)

        if self.bar_image and visible_width > 0:
            clip_rect = pygame.Rect(0, 0, visible_width, self.bar_height)
            bar_clip = self.bar_image.subsurface(clip_rect)
            screen.blit(bar_clip, (self.x, self.y))

        cup_x = self.x + visible_width - self.cup_icon_size[0] // 2
        # 调整耐心条奶茶杯位置
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
