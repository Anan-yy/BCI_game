"""模式选择器 - 循环切换游戏模式并显示预览"""

import pygame

from config import GAME_MODES
from menu.components import ClickParticle, MenuItem


class ModePreviewDisplay:
    """模式预览显示框 - 鼠标靠近时显示模式列表"""

    def __init__(self, x, y, font, title_font, mode_key="regular"):
        self.x = x
        self.y = y
        self.font = font
        self.title_font = title_font
        self.mode_key = mode_key
        self.alpha = 0
        self.target_alpha = 0
        self.width = 260
        self.height = 180

        self._mode_keys = ["regular", "challenge", "creative"]
        self._mode_colors = {
            "regular": ((60, 160, 100), (80, 200, 120)),
            "challenge": ((200, 80, 60), (240, 100, 80)),
            "creative": ((120, 80, 200), (150, 110, 240)),
        }

    def update(self, dt=0.016):
        self.alpha += (self.target_alpha - self.alpha) * 0.2

    def set_mode(self, mode_key):
        self.mode_key = mode_key
        self.target_alpha = 200

    def hide(self):
        self.target_alpha = 0

    def draw(self, screen):
        if self.alpha < 5:
            return

        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        pygame.draw.rect(
            surf,
            (30, 30, 40, int(self.alpha * 0.6)),
            (0, 0, self.width, self.height),
            border_radius=12,
        )
        pygame.draw.rect(
            surf,
            (255, 255, 255, int(self.alpha * 0.3)),
            (0, 0, self.width, self.height),
            2,
            border_radius=12,
        )

        btn_h = 45
        gap = 10
        start_y = 15

        for i, key in enumerate(self._mode_keys):
            bg, hover = self._mode_colors[key]
            is_active = key == self.mode_key

            y = start_y + i * (btn_h + gap)
            color = hover if is_active else bg
            alpha_color = (*color, int(self.alpha))
            pygame.draw.rect(surf, alpha_color, (10, y, self.width - 20, btn_h), border_radius=8)

            if is_active:
                pygame.draw.rect(
                    surf,
                    (255, 255, 255, int(self.alpha * 0.8)),
                    (10, y, self.width - 20, btn_h),
                    2,
                    border_radius=8,
                )

            name = GAME_MODES[key]["name"]
            txt = self.font.render(name, True, (255, 255, 255))
            txt.set_alpha(int(self.alpha))
            surf.blit(
                txt,
                (
                    10 + (self.width - 20 - txt.get_width()) // 2,
                    y + (btn_h - txt.get_height()) // 2,
                ),
            )

        screen.blit(surf, (self.x, self.y))


class ModeSelector(MenuItem):
    """模式选择按钮 - 点击循环切换模式，悬停显示模式信息"""

    def __init__(self, x, y, font, title_font, mode_keys=None):
        self.mode_keys = mode_keys or ["regular", "challenge", "creative"]
        self.current_index = 0
        self.font = font
        self.title_font = title_font
        self.x = x
        self.y = y

        self._mode_colors = {
            "regular": ((60, 160, 100), (80, 200, 120)),
            "challenge": ((200, 80, 60), (240, 100, 80)),
            "creative": ((120, 80, 200), (150, 110, 240)),
        }

        self._mode_icons = {
            "regular": "🍵",
            "challenge": "🔥",
            "creative": "✨",
        }

        self.hovered = False
        self.scale_t = 0.0
        self.click_t = 0.0
        self.ripple = 0.0

        _bg_color, _ = self._mode_colors[self.mode_keys[0]]
        padding = (50, 14)
        self.padding = padding
        self.radius = 20

        self._text_surf = title_font.render("模式选择", True, (255, 255, 255))
        w = self._text_surf.get_width() + padding[0] * 2
        h = self._text_surf.get_height() + padding[1] * 2
        self.rect = pygame.Rect(x - w // 2, y - h // 2, w, h)

        self.click_particles = []
        self.info_display = ModePreviewDisplay(
            self.rect.right + 20,
            self.rect.top - 10,
            font,
            title_font,
            self.mode_keys[0],
        )

    def _update_text(self):
        mode_key = self.mode_keys[self.current_index]
        self._text_surf = self.title_font.render("模式选择", True, (255, 255, 255))
        w = self._text_surf.get_width() + self.padding[0] * 2
        h = self._text_surf.get_height() + self.padding[1] * 2
        old_center = self.rect.center
        self.rect = pygame.Rect(old_center[0] - w // 2, old_center[1] - h // 2, w, h)
        self.info_display = ModePreviewDisplay(
            self.rect.right + 20,
            self.rect.top - 10,
            self.font,
            self.title_font,
            mode_key,
        )

    def cycle_mode(self):
        self.current_index = (self.current_index + 1) % len(self.mode_keys)
        self.click_t = 1.0
        self.ripple = 1.0
        self._update_text()
        mode_key = self.mode_keys[self.current_index]
        bg, _ = self._mode_colors.get(mode_key, ((100, 100, 100), (120, 120, 120)))

        for _ in range(20):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, bg))
        for _ in range(10):
            self.click_particles.append(ClickParticle(self.rect.centerx, self.rect.centery, (255, 255, 255)))

        return mode_key

    def update(self, dt=0.016):
        target = 1.0 if self.hovered else 0.0
        self.scale_t += (target - self.scale_t) * 0.15
        if self.click_t > 0:
            self.click_t -= dt * 3
        if self.ripple > 0:
            self.ripple -= dt * 2

        self.click_particles = [p for p in self.click_particles if p.update(dt)]
        self.info_display.update(dt)

    def draw(self, screen):
        s = 1.0 + 0.06 * self.scale_t
        w = int(self.rect.width * s)
        h = int(self.rect.height * s)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        mode_key = self.mode_keys[self.current_index]
        bg_color, hover_color = self._mode_colors.get(mode_key, ((100, 100, 100), (120, 120, 120)))
        color = hover_color if self.hovered else bg_color

        pygame.draw.rect(surf, color, (0, 0, w, h), border_radius=int(self.radius * s))

        if self.click_t > 0:
            click_color = (*color, int(self.click_t * 100))
            pygame.draw.rect(surf, click_color, (0, 0, w, h), border_radius=int(self.radius * s))

        if self.ripple > 0:
            ripple_r = int((1 - self.ripple) * max(w, h) * 0.3)
            ripple_surf = pygame.Surface((ripple_r * 2, ripple_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                ripple_surf,
                (255, 255, 255, int(self.ripple * 80)),
                (ripple_r, ripple_r),
                ripple_r,
            )
            screen.blit(
                ripple_surf,
                (self.rect.centerx - ripple_r, self.rect.centery - ripple_r),
            )

        tw = self._text_surf.get_width()
        th = self._text_surf.get_height()
        surf.blit(self._text_surf, ((w - tw) // 2, (h - th) // 2))

        screen.blit(surf, (self.rect.centerx - w // 2, self.rect.centery - h // 2))

        for p in self.click_particles:
            p.draw(screen)

        if self.hovered:
            self.info_display.set_mode(mode_key)
            self.info_display.draw(screen)

    def handle_event(self, event):
        """处理鼠标事件，返回模式 key 或 None"""
        if event.type == pygame.MOUSEMOTION:
            was_hovered = self.hovered
            self.hovered = self.rect.collidepoint(event.pos)
            if self.hovered:
                self.info_display.set_mode(self.mode_keys[self.current_index])
            elif was_hovered:
                self.info_display.hide()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return self.cycle_mode()
        return None
