"""游戏结束总结界面"""

import os

import pygame

from config import ASSETS_DIR, CHINESE_FONTS, SCREEN_HEIGHT, SCREEN_WIDTH


def _load_font(size):
    """辅助函数：加载中文字体"""
    for path in CHINESE_FONTS:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except (pygame.error, OSError):
                pass
    return pygame.font.Font(None, size)


class SummaryScreen:
    def __init__(self, screen, score, focus_value=0.0, game_mode="regular"):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.score = score
        self.focus_value = focus_value
        self.game_mode = game_mode

        # === 预设资源路径 (占位，后续替换真实图片即可) ===
        self.bg_path = os.path.join(
            ASSETS_DIR, "images", "backgrounds", "summary_bg.png"
        )
        self.icon_path = os.path.join(ASSETS_DIR, "images", "other", "summary_icon.png")

        # 加载背景
        self.bg = None
        if os.path.exists(self.bg_path):
            self.bg = pygame.image.load(self.bg_path).convert()
            self.bg = pygame.transform.scale(self.bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # 加载字体
        self.title_font = _load_font(72)
        self.info_font = _load_font(48)
        self.comment_font = _load_font(36)
        self.hint_font = _load_font(28)

        # 生成评语
        self.comment = self._generate_comment()

    def _generate_comment(self):
        """根据分数和专注力生成动态评语"""
        is_bci = self.game_mode == "bci"

        if is_bci:
            if self.score >= 200 and self.focus_value >= 70:
                return "专注大师！脑波与奶茶的完美共鸣！"
            if self.score >= 100:
                return "表现不错，继续保持专注！"
            if self.score >= 50:
                return "初露锋芒，调整呼吸再试一次！"
            return "万事开头难，放松心态，专注力会慢慢提升的！"
        else:
            if self.score >= 200:
                return "奶茶大师！你的手速快如闪电！"
            if self.score >= 100:
                return "手艺精湛！是一杯好奶茶！"
            if self.score >= 50:
                return "初露锋芒，再接再厉！"
            return "万事开头难，多喝奶茶多练习！"

    def run(self):
        while True:
            self.clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    return "menu"

            # === 绘制 ===
            if self.bg:
                self.screen.blit(self.bg, (0, 0))
            else:
                self.screen.fill((40, 40, 55))  # 深灰蓝备用背景

            # 标题
            title_surf = self.title_font.render("游戏结束", True, (255, 255, 255))
            self.screen.blit(
                title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 80)
            )

            # 分隔线
            pygame.draw.line(
                self.screen, (100, 100, 120), (200, 170), (SCREEN_WIDTH - 200, 170), 3
            )

            # 最终得分
            score_label = self.info_font.render("最终得分", True, (180, 180, 200))
            score_val = self.info_font.render(str(self.score), True, (255, 220, 100))
            self.screen.blit(
                score_label, (SCREEN_WIDTH // 2 - score_label.get_width() // 2, 210)
            )
            self.screen.blit(
                score_val, (SCREEN_WIDTH // 2 - score_val.get_width() // 2, 270)
            )

            # 专注力指标 (键盘模式强制显示 0)
            focus_label = self.info_font.render("平均专注力", True, (180, 180, 200))
            focus_val = self.info_font.render(
                f"{self.focus_value:.1f}%", True, (150, 255, 150)
            )
            self.screen.blit(
                focus_label, (SCREEN_WIDTH // 2 - focus_label.get_width() // 2, 360)
            )
            self.screen.blit(
                focus_val, (SCREEN_WIDTH // 2 - focus_val.get_width() // 2, 420)
            )

            # 评语
            comment_surf = self.comment_font.render(self.comment, True, (220, 220, 240))
            self.screen.blit(
                comment_surf, (SCREEN_WIDTH // 2 - comment_surf.get_width() // 2, 510)
            )

            # 返回提示
            hint_surf = self.hint_font.render(
                "按 任意键 / 点击屏幕 返回主菜单", True, (140, 140, 150)
            )
            self.screen.blit(
                hint_surf,
                (SCREEN_WIDTH // 2 - hint_surf.get_width() // 2, SCREEN_HEIGHT - 60),
            )

            pygame.display.flip()
