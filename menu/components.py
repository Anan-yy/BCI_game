"""菜单基础组件 - MenuItem 按钮和 ClickParticle 点击粒子"""

from __future__ import annotations

import math
import os
import random

import pygame


class ClickParticle:
    """点击特效粒子 - 从点击位置向外扩散的彩色粒子"""

    def __init__(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.x = float(x)
        self.y = float(y)
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 10)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(1.5, 3.0)
        self.size = random.randint(3, 8)

    def update(self, dt: float = 0.016) -> bool:
        self.life -= self.decay * dt
        if self.life <= 0:
            return False
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.96
        self.vy *= 0.96
        return True

    def draw(self, screen: pygame.Surface) -> None:
        alpha = int(self.life * 255)
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*self.color, alpha), (self.size, self.size), self.size)
        screen.blit(surf, (int(self.x) - self.size, int(self.y) - self.size))


class MenuItem:
    """菜单按钮组件，支持鼠标悬停动画和点击粒子效果"""

    def __init__(
        self,
        text: str,
        x: int,
        y: int,
        font: pygame.font.Font,
        bg_color: tuple[int, int, int],
        hover_color: tuple[int, int, int],
        text_color: tuple[int, int, int],
        padding: tuple[int, int] = (60, 18),
        radius: int = 20,
    ) -> None:
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.padding = padding
        self.radius = radius

        self._text_surf = font.render(text, True, text_color)
        w = self._text_surf.get_width() + padding[0] * 2
        h = self._text_surf.get_height() + padding[1] * 2
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

        self.hovered = False
        self.scale_t = 0.0
        self.click_t = 0.0
        self.click_particles = []

    def update(self, dt: float = 0.016) -> None:
        target = 1.0 if self.hovered else 0.0
        self.scale_t += (target - self.scale_t) * 0.15
        if self.click_t > 0:
            self.click_t -= dt * 3
        self.click_particles = [p for p in self.click_particles if p.update(dt)]

    def draw(self, screen: pygame.Surface) -> None:
        s = 1.0 + 0.06 * self.scale_t
        w = int(self.rect.width * s)
        h = int(self.rect.height * s)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        color = self.hover_color if self.hovered else self.bg_color
        self._draw_rounded_rect(surf, (0, 0, w, h), color, int(self.radius * s))

        if self.click_t > 0:
            click_color = (*color, int(self.click_t * 100))
            self._draw_rounded_rect(surf, (0, 0, w, h), click_color, int(self.radius * s))

        tw = self._text_surf.get_width()
        th = self._text_surf.get_height()
        surf.blit(self._text_surf, ((w - tw) // 2, (h - th) // 2))

        screen.blit(surf, (self.rect.centerx - w // 2, self.rect.centery - h // 2))

        for p in self.click_particles:
            p.draw(screen)

    def trigger_click(self) -> None:
        """触发点击粒子效果"""
        self.click_t = 1.0
        for _ in range(15):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, self.bg_color))
        for _ in range(8):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, (255, 255, 255)))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.trigger_click()
                return True
        return False

    @staticmethod
    def _draw_rounded_rect(
        surface: pygame.Surface,
        rect: tuple[int, int, int, int],
        color: tuple[int, ...],
        radius: int,
    ) -> None:
        pygame.draw.rect(surface, color, rect, border_radius=radius)


class Badge:
    """徽章组件，支持点击粒子爆开效果和悬停动画"""

    def __init__(
        self,
        images: list[str],
        x: int,
        y: int,
        size: tuple[int, int] = (60, 60),
    ) -> None:
        self.images = images
        self.x = x
        self.y = y
        self.size = size
        self.level = 0
        self.badge_surf = None
        self.hovered = False
        self.scale_t = 0.0
        self.click_particles = []
        self.hover_particles = []
        self._load_badge()

    def _load_badge(self) -> None:
        if self.level < len(self.images):
            path = self.images[self.level]
            if path and os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.badge_surf = pygame.transform.scale(img, self.size)
                    return
                except (pygame.error, OSError):
                    pass
        self.badge_surf = None

    def set_level(self, level: int) -> None:
        self.level = level
        self._load_badge()

    def get_rect(self) -> pygame.Rect:
        if self.badge_surf is None:
            return pygame.Rect(self.x, self.y, self.size[0], self.size[1])
        w, h = self.badge_surf.get_size()
        s = 1.0 + 0.1 * self.scale_t
        w, h = int(w * s), int(h * s)
        return pygame.Rect(self.x, self.y, w, h)

    def update(self, dt: float = 0.016) -> None:
        target = 1.0 if self.hovered else 0.0
        self.scale_t += (target - self.scale_t) * 0.15
        self.click_particles = [p for p in self.click_particles if p.update(dt)]
        self.hover_particles = [p for p in self.hover_particles if p.update(dt)]

    def draw(self, screen: pygame.Surface) -> None:
        s = 1.0 + 0.1 * self.scale_t
        if self.badge_surf:
            ow, oh = self.badge_surf.get_size()
            nw, nh = int(ow * s), int(oh * s)
            scaled = pygame.transform.scale(self.badge_surf, (nw, nh))
            screen.blit(scaled, (self.x, self.y))
        else:
            rect = self.get_rect()
            pygame.draw.rect(screen, (255, 215, 0), rect, border_radius=8)

        for p in self.hover_particles:
            p.draw(screen)
        for p in self.click_particles:
            p.draw(screen)

    def trigger_click(self) -> None:
        cx = self.x + self.size[0] // 2
        cy = self.y + self.size[1] // 2
        burst_colors = [(255, 215, 0), (255, 255, 255), (255, 180, 50)]
        for _ in range(20):
            color = random.choice(burst_colors)
            p = ClickParticle(cx, cy, color)
            p.size = random.randint(2, 6)
            p.vx *= 1.5
            p.vy *= 1.5
            p.decay = random.uniform(1.0, 2.0)
            self.click_particles.append(p)
        for _ in range(10):
            color = (255, 255, 200)
            p = ClickParticle(cx, cy, color)
            p.size = random.randint(1, 3)
            p.vx *= 2.0
            p.vy *= 2.0
            p.decay = random.uniform(0.8, 1.5)
            self.click_particles.append(p)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.get_rect().collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.get_rect().collidepoint(event.pos):
                self.trigger_click()
                return True
        return False
