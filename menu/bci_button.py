"""BCI模式按钮 - 带脉冲动画和发光特效"""

from __future__ import annotations

import math
import random

import pygame

from menu.components import ClickParticle, MenuItem


class BCIModeButton(MenuItem):
    """脑机接口模式按钮 - 带有特殊脉冲动画和发光效果以突出显示"""

    def __init__(self, text: str, x: int, y: int, font: pygame.font.Font, title_font: pygame.font.Font) -> None:
        self.text = text
        self.font = font
        self.title_font = title_font
        self.bg_color = (0, 120, 180)
        self.hover_color = (0, 160, 220)
        self.text_color = (255, 255, 255)
        self.padding = (50, 18)
        self.radius = 25

        self._text_surf = title_font.render("脑机接口", True, (255, 255, 255))
        w = self._text_surf.get_width() + self.padding[0] * 2
        h = self._text_surf.get_height() + self.padding[1] * 2
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

        self.hovered = False
        self.scale_t = 0.0
        self.click_t = 0.0
        self.click_particles = []
        self.pulse_t = 0.0
        self.glow_particles = []

    def update(self, dt: float = 0.016) -> None:
        target = 1.0 if self.hovered else 0.0
        self.scale_t += (target - self.scale_t) * 0.15
        if self.click_t > 0:
            self.click_t -= dt * 3
        self.click_particles = [p for p in self.click_particles if p.update(dt)]

        self.pulse_t += dt * 3
        if self.hovered and random.random() < 0.3:
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(self.rect.width / 2, self.rect.width / 2 + 20)
            px = self.rect.centerx + math.cos(angle) * r
            py = self.rect.centery + math.sin(angle) * r
            self.glow_particles.append(ClickParticle(px, py, (0, 180, 255)))
        self.glow_particles = [p for p in self.glow_particles if p.update(dt)]

    def draw(self, screen: pygame.Surface) -> None:
        pulse = math.sin(self.pulse_t) * 0.5 + 0.5
        glow_alpha = int(60 + pulse * 80)

        glow_size = int(5 + pulse * 8)
        glow_surf = pygame.Surface(
            (self.rect.width + glow_size * 2, self.rect.height + glow_size * 2),
            pygame.SRCALPHA,
        )
        pygame.draw.rect(
            glow_surf,
            (0, 150, 200, glow_alpha),
            (0, 0, glow_surf.get_width(), glow_surf.get_height()),
            border_radius=self.radius + glow_size,
        )
        screen.blit(
            glow_surf,
            (self.rect.x - glow_size, self.rect.y - glow_size),
        )

        s = 1.0 + 0.08 * self.scale_t + pulse * 0.02
        w = int(self.rect.width * s)
        h = int(self.rect.height * s)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        color = self.hover_color if self.hovered else self.bg_color
        border_color = (100, 220, 255) if self.hovered else (0, 180, 255)
        pygame.draw.rect(surf, color, (0, 0, w, h), border_radius=int(self.radius * s))
        pygame.draw.rect(surf, border_color, (0, 0, w, h), 3, border_radius=int(self.radius * s))

        if self.click_t > 0:
            click_color = (*color, int(self.click_t * 150))
            pygame.draw.rect(surf, click_color, (0, 0, w, h), border_radius=int(self.radius * s))

        tw = self._text_surf.get_width()
        th = self._text_surf.get_height()
        surf.blit(self._text_surf, ((w - tw) // 2, (h - th) // 2))

        screen.blit(surf, (self.rect.centerx - w // 2, self.rect.centery - h // 2))

        for p in self.glow_particles:
            p.draw(screen)
        for p in self.click_particles:
            p.draw(screen)

    def trigger_click(self) -> None:
        self.click_t = 1.0
        for _ in range(25):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, (0, 180, 255)))
        for _ in range(12):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, (255, 255, 255)))
