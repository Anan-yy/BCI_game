"""资源管理器 - 统一加载、缓存和管理游戏资源"""

import logging
import os

import pygame

from config import ASSETS_DIR

logger = logging.getLogger(__name__)


class AssetManager:
    """集中管理游戏资源（图片、字体），提供缓存和错误处理

    使用方式:
        assets = AssetManager()
        bg = assets.load_image("backgrounds/奶茶店2.png")
        font = assets.load_font("ZCOOLKuaiLe-Regular.ttf", size=36)
    """

    def __init__(self):
        self._image_cache = {}
        self._font_cache = {}
        self._images_dir = os.path.join(ASSETS_DIR, "images")
        self._fonts_dir = os.path.join(ASSETS_DIR, "fonts")

    def load_image(self, path: str, size: tuple[int, int] | None = None) -> pygame.Surface:
        """加载图片，优先使用缓存

        参数:
            path: 图片路径（绝对路径或相对于 images 目录的相对路径）
            size: 缩放尺寸 (width, height)，为 None 则不缩放

        返回:
            pygame.Surface 对象，加载失败返回品红色占位图
        """
        cache_key = (path, size)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        full_path = path if os.path.isabs(path) else os.path.join(self._images_dir, path)

        surface = self._load_image_file(full_path, size)
        self._image_cache[cache_key] = surface
        return surface

    def _load_image_file(self, path: str, size: tuple[int, int] | None) -> pygame.Surface:
        if os.path.exists(path):
            try:
                surface = pygame.image.load(path).convert_alpha()
                if size:
                    surface = pygame.transform.scale(surface, size)
                return surface
            except (pygame.error, OSError) as e:
                logger.warning("图片加载失败 %s: %s", path, e)
        else:
            logger.debug("图片文件不存在: %s", path)

        return self._create_placeholder(size or (64, 64), "IMG")

    def load_font(self, font_name: str, size: int) -> pygame.font.Font:
        """加载字体，优先使用缓存

        参数:
            font_name: 字体文件名或系统字体名称
            size: 字体大小

        返回:
            pygame.font.Font 对象，加载失败返回默认字体
        """
        cache_key = (font_name, size)
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        font_path = os.path.join(self._fonts_dir, font_name)
        if os.path.exists(font_path):
            try:
                font = pygame.font.Font(font_path, size)
                self._font_cache[cache_key] = font
                return font
            except (pygame.error, OSError) as e:
                logger.warning("字体加载失败 %s: %s", font_path, e)

        try:
            font = pygame.font.SysFont(font_name, size)
        except Exception:
            font = pygame.font.Font(pygame.font.get_default_font(), size)

        self._font_cache[cache_key] = font
        return font

    def preload_images(self, paths: list[str], size: tuple[int, int] | None = None):
        """批量预加载图片到缓存"""
        for path in paths:
            self.load_image(path, size)

    def clear_cache(self):
        """清空所有缓存"""
        self._image_cache.clear()
        self._font_cache.clear()

    @staticmethod
    def _create_placeholder(size: tuple[int, int], label: str) -> pygame.Surface:
        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill((255, 0, 255, 128))
        font = pygame.font.Font(pygame.font.get_default_font(), min(size) // 4)
        text = font.render(label, True, (255, 255, 255))
        text_rect = text.get_rect(center=(size[0] // 2, size[1] // 2))
        surface.blit(text, text_rect)
        return surface
