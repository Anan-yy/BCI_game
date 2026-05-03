"""BCI设置页面 - 配置科创平台TCP服务器连接参数"""

from __future__ import annotations

import pygame

from bci.config import load_bci_config, save_bci_config
from config import SCREEN_HEIGHT, SCREEN_WIDTH
from menu.components import MenuItem
from menu.text_input import TextInputBox


class BCISettingsScreen:
    """BCI连接设置页面"""

    def __init__(self, screen: pygame.Surface, font: pygame.font.Font, title_font: pygame.font.Font) -> None:
        self.screen = screen
        self.font = font
        self.title_font = title_font
        self.clock = pygame.time.Clock()
        self.running = True
        self.result = None

        bci_config = load_bci_config()

        self.ip_input = TextInputBox(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 - 40,
            300,
            40,
            font,
            default_text=bci_config["server_ip"],
            label="服务器IP:",
        )
        self.port_input = TextInputBox(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 + 40,
            300,
            40,
            font,
            default_text=str(bci_config["server_port"]),
            label="端口号:",
        )

        self.test_btn = MenuItem(
            "测试连接",
            SCREEN_WIDTH // 2 - 120,
            SCREEN_HEIGHT // 2 + 130,
            font,
            (0, 120, 180),
            (0, 150, 220),
            (255, 255, 255),
            padding=(50, 15),
            radius=15,
        )
        self.back_btn = MenuItem(
            "返回",
            SCREEN_WIDTH // 2 - 60,
            SCREEN_HEIGHT // 2 + 210,
            font,
            (80, 80, 80),
            (100, 100, 100),
            (255, 255, 255),
            padding=(50, 15),
            radius=15,
        )

        self.status_text = ""
        self.status_color = (255, 255, 255)

    def run(self) -> str | None:
        """运行设置页面"""
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    self.result = "quit"
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._save_and_close()
                else:
                    self.ip_input.handle_event(event)
                    self.port_input.handle_event(event)
                    if self.test_btn.handle_event(event):
                        self._test_connection()
                    if self.back_btn.handle_event(event):
                        self._save_and_close()

            self._update(dt)
            self._draw()
            pygame.display.flip()

        return self.result

    def _save_and_close(self) -> None:
        """保存配置并关闭"""
        ip = self.ip_input.get_text()
        try:
            port = int(self.port_input.get_text())
            save_bci_config(ip, port)
            self.status_text = "配置已保存"
            self.status_color = (100, 255, 100)
        except ValueError:
            self.status_text = "端口号格式错误，未保存"
            self.status_color = (255, 100, 100)
            return

        pygame.display.flip()
        pygame.time.wait(500)
        self.running = False
        self.result = "back"

    def _test_connection(self) -> None:
        """测试BCI连接"""
        ip = self.ip_input.get_text()
        try:
            port = int(self.port_input.get_text())
        except ValueError:
            self.status_text = "端口号格式错误"
            self.status_color = (255, 100, 100)
            return

        self.status_text = "正在连接..."
        self.status_color = (255, 255, 100)
        pygame.display.flip()

        from bci.data_reader import BCIDataReader

        reader = BCIDataReader()
        connected = reader.connect(ip, port)
        reader.disconnect()

        if connected:
            self.status_text = "连接成功！"
            self.status_color = (100, 255, 100)
        else:
            self.status_text = "连接失败，请检查IP和端口"
            self.status_color = (255, 100, 100)

    def _update(self, dt: float) -> None:
        self.ip_input.update(dt)
        self.port_input.update(dt)
        self.test_btn.update(dt)
        self.back_btn.update(dt)

    def _draw(self) -> None:
        self.screen.fill((30, 30, 40))

        title = self.title_font.render("脑机接口设置", True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

        desc = self.font.render("配置科创平台TCP服务器连接参数", True, (180, 180, 180))
        self.screen.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, 130))

        self.ip_input.draw(self.screen)
        self.port_input.draw(self.screen)

        self.test_btn.draw(self.screen)
        self.back_btn.draw(self.screen)

        if self.status_text:
            status = self.font.render(self.status_text, True, self.status_color)
            self.screen.blit(
                status,
                (SCREEN_WIDTH // 2 - status.get_width() // 2, SCREEN_HEIGHT // 2 + 270),
            )

        hint = self.font.render("ESC 返回主菜单", True, (100, 100, 100))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 50))
