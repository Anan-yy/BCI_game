"""游戏设置页面 - 包含BCI设置等子设置项"""

import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH
from menu.bci_button import BCIModeButton
from menu.components import MenuItem
from menu.screens.bci_settings import BCISettingsScreen


class GameSettingsScreen:
    """游戏设置页面，包含BCI设置等子设置项"""

    def __init__(self, screen, font, title_font):
        self.screen = screen
        self.font = font
        self.title_font = title_font
        self.clock = pygame.time.Clock()
        self.running = True
        self.result = None

        cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

        self.bci_btn = BCIModeButton("BCI设置", cx, cy - 40, font, title_font)
        self.back_btn = MenuItem(
            "返回",
            cx,
            cy + 60,
            title_font,
            (80, 80, 80),
            (100, 100, 100),
            (255, 255, 255),
            padding=(50, 15),
            radius=15,
        )

    def run(self):
        """运行设置页面"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.result = "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                        self.result = "back"
                else:
                    if self.bci_btn.handle_event(event):
                        bci_settings = BCISettingsScreen(
                            self.screen, self.font, self.title_font
                        )
                        bci_settings.run()
                    if self.back_btn.handle_event(event):
                        self.running = False
                        self.result = "back"

            self._update(dt)
            self._draw()
            pygame.display.flip()

        return self.result

    def _update(self, dt):
        self.bci_btn.update(dt)
        self.back_btn.update(dt)

    def _draw(self):
        self.screen.fill((30, 30, 40))

        title = self.title_font.render("游戏设置", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        desc = self.font.render("请选择需要配置的项目", True, (180, 180, 180))
        self.screen.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, 160))

        self.bci_btn.draw(self.screen)
        self.back_btn.draw(self.screen)

        hint = self.font.render("ESC 返回主菜单", True, (100, 100, 100))
        self.screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50)
        )
