"""粒子系统 - 浮动装饰粒子和蒸汽粒子"""

import math
import random

import pygame


class FloatingItem:
    """浮动装饰粒子 - 在主菜单背景中浮动"""

    def __init__(self, screen_w, screen_h, color=None):
        self.x = random.uniform(0, screen_w)
        self.y = random.uniform(0, screen_h)
        self.color = color or (
            random.randint(150, 255),
            random.randint(100, 200),
            random.randint(50, 150),
        )
        self.size = random.randint(12, 30)
        self.speed_x = random.uniform(-0.5, 0.5)
        self.speed_y = random.uniform(-0.3, -0.05)
        self.phase = random.uniform(0, 2 * math.pi)
        self.screen_w = screen_w
        self.screen_h = screen_h

    def update(self):
        self.x += self.speed_x + math.sin(self.phase) * 0.5
        self.y += self.speed_y
        self.phase += 0.02
        if self.y < -self.size * 2:
            self.y = self.screen_h + self.size
            self.x = random.uniform(0, self.screen_w)
        if self.x < -self.size * 2:
            self.x = self.screen_w + self.size
        elif self.x > self.screen_w + self.size * 2:
            self.x = -self.size

    def draw(self, screen):
        alpha = 120
        surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            surf, (*self.color, alpha), (self.size, self.size), self.size // 2
        )
        screen.blit(surf, (int(self.x) - self.size, int(self.y) - self.size))


class SteamParticle:
    """蒸汽粒子 - 奶茶杯上升的热气效果"""

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-1.5, -0.5)
        self.life = 1.0
        self.decay = random.uniform(0.01, 0.025)
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.vx + math.sin(self.life * 5) * 0.3
        self.y += self.vy
        self.life -= self.decay
        return self.life > 0

    def draw(self, screen):
        alpha = int(self.life * 80)
        if alpha > 0:
            surf = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                surf, (255, 255, 255, alpha), (self.size, self.size), self.size
            )
            screen.blit(surf, (int(self.x) - self.size, int(self.y) - self.size))
