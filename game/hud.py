"""游戏 HUD 模块 - 专注力茶壶 UI + HUD 渲染逻辑"""

import os

import pygame

from config import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)


class FocusTeapotUI:
    """专注力茶壶 UI - 液面高度代表专注力数值（0-100）"""

    def __init__(self, image_path=None, x=10, y=90, width=100, height=120):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.focus_value = 0
        self._liquid_color = (144, 238, 144)
        self._teapot_img = None

        if image_path and os.path.exists(image_path):
            try:
                self._teapot_img = pygame.image.load(image_path).convert_alpha()
                self._teapot_img = pygame.transform.scale(self._teapot_img, (self.width, self.height))
            except (pygame.error, OSError):
                pass

    def update(self, value):
        """更新专注力数值并计算当前液体颜色"""
        self.focus_value = max(0, min(100, value))
        t = self.focus_value / 100.0
        r = int(144 + (255 - 144) * t)
        g = int(238 + (215 - 238) * t)
        b = int(144 + (0 - 144) * t)
        self._liquid_color = (r, g, b)

    def draw(self, screen):
        """绘制茶壶 UI"""
        if self._teapot_img:
            screen.blit(self._teapot_img, (self.x, self.y))
        else:
            self._draw_fallback(screen)

    def _draw_fallback(self, screen):
        """无图片时的备用绘制方案"""
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        body_r = self.width * 0.38

        handle_rect = pygame.Rect(cx + body_r - 5, cy - body_r * 0.6, self.width * 0.35, body_r * 1.2)
        pygame.draw.rect(screen, (139, 69, 19), handle_rect, 6, border_radius=10)

        spout_pts = [
            (cx - body_r + 5, cy - body_r * 0.2),
            (cx - body_r - self.width * 0.35, cy - body_r * 0.8),
            (cx - body_r - self.width * 0.25, cy - body_r * 0.6),
            (cx - body_r + 5, cy + body_r * 0.4),
        ]
        pygame.draw.polygon(screen, (139, 69, 19), spout_pts, 6)

        body_rect = pygame.Rect(cx - body_r, cy - body_r, body_r * 2, body_r * 2)

        liquid_h = body_rect.height * (self.focus_value / 100.0)
        if liquid_h > 0:
            clip_surf = pygame.Surface((body_rect.width, body_rect.height), pygame.SRCALPHA)
            pygame.draw.ellipse(clip_surf, (255, 255, 255), (0, 0, body_rect.width, body_rect.height))
            pygame.draw.rect(
                clip_surf,
                self._liquid_color,
                (0, body_rect.height - liquid_h, body_rect.width, liquid_h),
            )
            if liquid_h > 4:
                pygame.draw.line(
                    clip_surf,
                    (255, 255, 255),
                    (4, body_rect.height - liquid_h + 2),
                    (body_rect.width - 4, body_rect.height - liquid_h + 2),
                    2,
                )
            screen.blit(clip_surf, (body_rect.x, body_rect.y))

        glass_surf = pygame.Surface((body_rect.width, body_rect.height), pygame.SRCALPHA)
        pygame.draw.ellipse(glass_surf, (200, 200, 200, 80), (0, 0, body_rect.width, body_rect.height))
        screen.blit(glass_surf, (body_rect.x, body_rect.y))
        pygame.draw.ellipse(screen, (139, 69, 19), body_rect, 6)

        lid_rect = pygame.Rect(cx - body_r * 0.8, cy - body_r - 10, body_r * 1.6, 14)
        pygame.draw.rect(screen, (139, 69, 19), lid_rect, 6, border_radius=8)
        knob_rect = pygame.Rect(cx - 8, cy - body_r - 18, 16, 10)
        pygame.draw.ellipse(screen, (160, 82, 45), knob_rect)

        font = pygame.font.Font(None, 28)
        val_surf = font.render(f"{int(self.focus_value)}", True, (255, 255, 255))
        screen.blit(
            val_surf,
            (
                body_rect.x + (body_rect.width - val_surf.get_width()) // 2,
                body_rect.y + body_rect.height // 2 - val_surf.get_height() // 2,
            ),
        )


def draw_hud(
    screen,
    score_manager,
    mode_name,
    patience_bar,
    font,
    hint_font,
    recipe_font,
    focus_teapot=None,
    attention=None,
    smoothed_yaw=0,
    bci_mode=False,
    free_combine=False,
    recipe_result=None,
    creative_ingredients=None,
    attention_curve=None,
    bci_connected=False,
):
    """统一绘制游戏 HUD"""
    score_text = font.render(f"分数: {score_manager.score}", True, (0, 0, 0))
    screen.blit(score_text, (10, 10))

    mode_text = font.render(f"{mode_name}", True, (100, 50, 150))
    screen.blit(mode_text, (10, 50))

    if focus_teapot:
        if attention is not None:
            focus_teapot.update(attention)
        else:
            focus_teapot.update(0)
        focus_teapot.draw(screen)

    patience_bar.draw(screen)

    if bci_mode and attention is not None:
        if free_combine and attention_curve:
            multiplier = attention_curve.map_attention(attention)
            tier = attention_curve.get_rating_tier(attention)
            bci_text = hint_font.render(
                f"{tier} x{multiplier:.2f}",
                True,
                (255, 255, 255),
            )
        else:
            bci_text = hint_font.render(
                f"头动: {smoothed_yaw:.1f}",
                True,
                (255, 255, 255),
            )
        screen.blit(bci_text, (10, 235))
    elif bci_mode and attention is None:
        bci_text = hint_font.render("BCI设备未连接", True, (200, 0, 0))
        screen.blit(bci_text, (10, 235))

    if free_combine and recipe_result:
        recipe_name = recipe_result["recipe_name"]
        rating = recipe_result["rating"]
        total_score = recipe_result["total_score"]

        name_surf = recipe_font.render(f"{rating['emoji']} {recipe_name}", True, rating["color"])
        screen.blit(name_surf, (SCREEN_WIDTH // 2 - name_surf.get_width() // 2, 10))

        grade_surf = recipe_font.render(f"评分: {rating['name']} ({total_score})", True, rating["color"])
        screen.blit(grade_surf, (SCREEN_WIDTH // 2 - grade_surf.get_width() // 2, 45))

        if creative_ingredients:
            ing_text = hint_font.render(f"食材: {' + '.join(creative_ingredients)}", True, (80, 80, 80))
            screen.blit(ing_text, (SCREEN_WIDTH // 2 - ing_text.get_width() // 2, 80))

    if bci_mode:
        hint_text = "脑机接口模式 | ESC 返回"
    elif free_combine:
        hint_text = "自由搭配，创造你的专属奶茶 | ESC 返回"
    else:
        hint_text = "方向键: 左右移动 | ESC: 返回"

    hint1 = hint_font.render(hint_text, True, (50, 50, 50))
    screen.blit(hint1, (10, SCREEN_HEIGHT - 40))

    attention_value = attention if attention is not None else 0
    attention_text = f"注意力: {int(attention_value)}"
    attention_surface = font.render(attention_text, True, (0, 255, 0) if bci_connected else (255, 0, 0))
    attention_rect = attention_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(attention_surface, attention_rect)
