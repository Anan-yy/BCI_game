"""
食材管理器模块 - 控制食材的生成时机和类型
"""

import random
import time

from config import *
from game.sprites import Ingredient


class IngredientManager:
    """
    食材生成管理器，负责按间隔生成随机食材

    参数:
        无外部参数，使用 config.py 中的全局配置
    """

    def __init__(self):
        self.ingredients = []  # 当前活跃食材列表（未使用）
        self.last_spawn_time = time.time()  # 上一次生成食材的时间戳
        self.spawn_interval = (
            INGREDIENT_SPAWN_INTERVAL / 1000.0
        )  # 生成间隔（秒），INGREDIENT_SPAWN_INTERVAL=1000 毫秒
        self.last_type = None  # 上一次生成的食材类型，用于避免重复

    def should_spawn(self):
        """
        判断是否应该生成新食材

        返回:
            True 表示时间到达生成间隔，应生成新食材
            False 表示还需等待
        """
        current_time = time.time()
        if current_time - self.last_spawn_time >= self.spawn_interval:
            self.last_spawn_time = current_time
            return True
        return False

    def spawn_ingredient(self, required_types=None):
        """
        生成一个新食材

        参数:
            required_types: 必接食材类型列表，如 ["红茶"]

        返回:
            Ingredient 精灵对象
        """
        # 避免连续掉同一食材
        available_types = [t for t in INGREDIENT_TYPES if t != self.last_type]
        if not available_types:
            available_types = INGREDIENT_TYPES

        ing_type = random.choice(available_types)
        self.last_type = ing_type

        is_required = False
        if required_types and ing_type in required_types:
            is_required = True

        return Ingredient(ing_type, is_required)

    def update(self, required_types=None):
        """
        每帧调用，判断是否需要生成食材

        参数:
            required_types: 必接食材类型列表

        返回:
            新生成的 Ingredient 对象，或 None（不需要生成时）
        """
        if self.should_spawn():
            ingredient = self.spawn_ingredient(required_types)
            return ingredient
        return None
