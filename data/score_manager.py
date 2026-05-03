"""
分数和金钱管理系统 - 跟踪玩家得分、金钱、必接食材状态
"""

import logging

logger = logging.getLogger(__name__)


class ScoreManager:
    """
    分数和金钱管理系统

    属性:
        score: 总分，接到食材时累加
        money: 总金钱，用于衡量本杯收益
        current_cup_ingredients: 当前杯子已接住的食材列表
        has_required: 是否已接住必接食材（接到后才能累积本杯金钱）
        required_ingredient: 当前杯子的必接食材类型
    """

    def __init__(self):
        self.score = 0
        self.money = 0
        self.current_cup_ingredients = []  # 当前杯子的食材列表
        self.has_required = False  # 是否已接到必接食材
        self.required_ingredient = None  # 当前必接食材名称

    def set_required_ingredient(self, ingredient_type):
        """
        设置当前杯子的必接食材

        参数:
            ingredient_type: 必接食材名称，如 "红茶"
        """
        self.required_ingredient = ingredient_type
        self.has_required = False
        self.current_cup_ingredients = []

    def add_ingredient(self, ingredient_type, is_required=False):
        """
        接住食材，计算分数和金钱

        规则:
            - 接到必接食材前：只加分，不加金钱
            - 接到必接食材后：加分 + 加金钱

        参数:
            ingredient_type: 食材名称
            is_required: 是否为必接食材
        """
        from config import INGREDIENT_POINTS

        points = INGREDIENT_POINTS.get(ingredient_type, 5)  # 默认 5 分

        if is_required:
            self.has_required = True
            self.money += points
            logger.info("接住必接食材 %s，获得 %s 金钱", ingredient_type, points)
        elif self.has_required:
            # 已接到必接，后续食材正常加分加金钱
            self.money += points
            logger.info("接住选接食材 %s，获得 %s 金钱", ingredient_type, points)
        else:
            # 未接到必接，只加分不加金钱
            logger.debug("未接到必接食材，%s 无效", ingredient_type)

        self.score += points
        self.current_cup_ingredients.append(ingredient_type)

    def finish_cup(self):
        """
        完成一杯奶茶，结算并重置状态

        规则:
            - 未接到必接食材：扣 10 金钱作为惩罚
        """
        if not self.has_required:
            self.money = max(0, self.money - 10)  # 扣罚 10 金钱，最低为 0
            logger.warning("未接到必接食材，整杯单价归零！")

        logger.info("本杯完成！当前总分: %s, 总金钱: %s", self.score, self.money)
        self.has_required = False
        self.current_cup_ingredients = []

    def draw(self, screen, font):
        """
        在屏幕上绘制分数和金钱信息

        参数:
            screen: pygame 屏幕对象
            font: 字体对象
        """
        score_text = font.render(f"分数: {self.score}", True, (0, 0, 0))
        money_text = font.render(f"金钱: {self.money}", True, (0, 100, 0))
        screen.blit(score_text, (10, 10))  # 分数显示在左上角
        screen.blit(money_text, (10, 50))  # 金钱显示在分数下方
