"""文本输入框 - 用于BCI设置页面的IP和端口输入"""

from __future__ import annotations

import pygame


class TextInputBox:
    """文本输入框"""

    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        font: pygame.font.Font,
        default_text: str = "",
        label: str = "",
        max_length: int = 20,
    ) -> None:
        self.rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.label = label
        self.text = default_text
        self.max_length = max_length
        self.active = False
        self.color_inactive = (100, 100, 100)
        self.color_active = (0, 150, 200)
        self.color = self.color_inactive
        self.blink_t = 0.0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = self.color_active if self.active else self.color_inactive
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
                self.color = self.color_inactive
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(self.text) < self.max_length:
                char = event.unicode
                if char.isprintable():
                    self.text += char

    def update(self, dt: float) -> None:
        self.blink_t += dt * 4

    def draw(self, screen: pygame.Surface) -> None:
        label_surf = self.font.render(self.label, True, (200, 200, 200))
        screen.blit(label_surf, (self.rect.x, self.rect.y - 30))

        pygame.draw.rect(screen, self.color, self.rect, 2, border_radius=8)

        bg_color = (*self.color[:3], 30) if self.active else (40, 40, 50, 50)
        surf = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, bg_color, (0, 0, *self.rect.size), border_radius=8)
        screen.blit(surf, self.rect.topleft)

        text_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surf, (self.rect.x + 10, self.rect.y + 5))

        if self.active and int(self.blink_t) % 2 == 0:
            cursor_x = self.rect.x + 10 + text_surf.get_width()
            pygame.draw.line(
                screen,
                (255, 255, 255),
                (cursor_x, self.rect.y + 8),
                (cursor_x, self.rect.y + self.rect.h - 8),
                2,
            )

    def get_text(self) -> str:
        return self.text
