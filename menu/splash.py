"""游戏启动过场动画"""

from __future__ import annotations

import sys

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH


def _render_text_with_outline(
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int],
    outline_color: tuple[int, int, int],
    outline_width: int = 2,
) -> list[tuple[pygame.Surface, tuple[int, int]]]:
    """渲染带描边的文字"""
    texts = []
    # 渲染中心文字
    main_surf = font.render(text, True, color)
    # 渲染 8 个方向的边框文字
    for dx, dy in [
        (-outline_width, 0),
        (outline_width, 0),
        (0, -outline_width),
        (0, outline_width),
        (-outline_width, -outline_width),
        (outline_width, -outline_width),
        (-outline_width, outline_width),
        (outline_width, outline_width),
    ]:
        surf = font.render(text, True, outline_color)
        texts.append((surf, (dx, dy)))

    texts.append((main_surf, (0, 0)))
    return texts


class SplashScreen:
    """游戏启动动画：文字从左至右渐进显现，再从左至右快速消失"""

    def __init__(self, screen: pygame.Surface, title_font: pygame.font.Font) -> None:
        self.screen = screen
        self.title_font = title_font
        self.clock = pygame.time.Clock()

        # 颜色定义
        self.red_bean_color = (150, 20, 20)  # 红豆色
        self.light_gray_color = (190, 190, 190)  # 淡灰色
        self.outline_color = (20, 20, 20)  # 深灰色边框

        self.text1 = "霸王茶"
        self.text2 = "In-store"

        # 预渲染文字部件
        self.parts1 = _render_text_with_outline(self.title_font, self.text1, self.red_bean_color, self.outline_color, 6)
        self.parts2 = _render_text_with_outline(
            self.title_font, self.text2, self.light_gray_color, self.outline_color, 6
        )

        # 计算总尺寸
        w1 = max(s.get_width() for s, _ in self.parts1)
        h1 = max(s.get_height() for s, _ in self.parts1)
        w2 = max(s.get_width() for s, _ in self.parts2)
        h2 = max(s.get_height() for s, _ in self.parts2)

        gap = 10  # 间距
        total_w = w1 + w2 + gap + 10  # +10 for outline margin
        total_h = max(h1, h2) + 10

        # 创建合并后的 Surface
        self.combined_surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

        # 绘制到 Surface
        y1 = (total_h - h1) // 2
        y2 = (total_h - h2) // 2
        x1 = 5
        x2 = w1 + gap + 5

        for surf, offset in self.parts1:
            self.combined_surf.blit(surf, (x1 + offset[0], y1 + offset[1]))
        for surf, offset in self.parts2:
            self.combined_surf.blit(surf, (x2 + offset[0], y2 + offset[1]))

        # 裁剪区域
        self.full_w = total_w
        self.full_h = total_h
        # 位置调整：下移至屏幕 1/3 处
        self.base_x = (SCREEN_WIDTH - self.full_w) // 2
        self.base_y = SCREEN_HEIGHT // 3

    def run(self) -> None:
        start_ticks = pygame.time.get_ticks()

        # 动画时间控制（毫秒）
        t_appear = 1000  # 显现时间
        t_stay = 600  # 停留时间
        t_vanish = 400  # 消失时间
        t_total = t_appear + t_stay + t_vanish

        while True:
            elapsed = pygame.time.get_ticks() - start_ticks
            if elapsed > t_total:
                break

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    return  # 按键跳过

            # 绘制灰色背景
            self.screen.fill((50, 50, 50))

            area = pygame.Rect(0, 0, self.full_w, self.full_h)
            dest_x = self.base_x

            # 1. 显现阶段：从左至右生长
            if elapsed < t_appear:
                t = self._smoothstep(elapsed / t_appear)
                w = int(self.full_w * t)
                area = pygame.Rect(0, 0, w, self.full_h)
                dest_x = self.base_x

            # 2. 停留阶段
            elif elapsed < t_appear + t_stay:
                area = pygame.Rect(0, 0, self.full_w, self.full_h)
                dest_x = self.base_x

            # 3. 消失阶段：从左至右擦除
            else:
                elapsed_vanish = elapsed - (t_appear + t_stay)
                t = self._smoothstep(elapsed_vanish / t_vanish)

                cut_w = int(self.full_w * t)
                remaining_w = self.full_w - cut_w

                if remaining_w > 0:
                    area = pygame.Rect(cut_w, 0, remaining_w, self.full_h)
                    dest_x = self.base_x + cut_w
                else:
                    continue

            self.screen.blit(self.combined_surf, (dest_x, self.base_y), area)
            pygame.display.flip()
            self.clock.tick(60)

    def _smoothstep(self, t: float) -> float:
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)
