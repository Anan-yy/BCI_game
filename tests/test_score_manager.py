"""ScoreManager 单元测试"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.score_manager import ScoreManager


class TestScoreManager:
    def test_initial_state(self):
        sm = ScoreManager()
        assert sm.score == 0
        assert sm.money == 0
        assert sm.has_required is False
        assert sm.required_ingredient is None
        assert sm.current_cup_ingredients == []

    def test_set_required_ingredient(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        assert sm.required_ingredient == "红茶"
        assert sm.has_required is False

    def test_add_required_ingredient(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("红茶", is_required=True)
        assert sm.has_required is True
        assert sm.money == 8  # 红茶分值为 8
        assert "红茶" in sm.current_cup_ingredients

    def test_add_ingredient_before_required(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("珍珠", is_required=False)
        assert sm.has_required is False
        assert sm.money == 0  # 未接到必接食材，不加金钱
        assert sm.score > 0  # 但仍然加分

    def test_add_ingredient_after_required(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("红茶", is_required=True)
        sm.add_ingredient("珍珠", is_required=False)
        assert sm.has_required is True
        assert sm.money == 18  # 红茶 8 + 珍珠 10

    def test_finish_cup_without_required(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("珍珠", is_required=False)
        sm.finish_cup()
        assert sm.money == 0  # 扣罚后仍为 0
        assert sm.has_required is False
        assert sm.current_cup_ingredients == []

    def test_finish_cup_with_required(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("红茶", is_required=True)
        sm.add_ingredient("珍珠", is_required=False)
        sm.finish_cup()
        assert sm.money == 18
        assert sm.has_required is False
        assert sm.current_cup_ingredients == []

    def test_score_accumulation(self):
        sm = ScoreManager()
        sm.set_required_ingredient("红茶")
        sm.add_ingredient("红茶", is_required=True)
        sm.add_ingredient("牛奶", is_required=False)
        sm.add_ingredient("珍珠", is_required=False)
        assert sm.score == 23  # 8 + 5 + 10

    def test_unknown_ingredient_default_points(self):
        sm = ScoreManager()
        sm.add_ingredient("未知食材", is_required=False)
        assert sm.score == 5  # 默认 5 分
