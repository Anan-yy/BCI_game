"""配方评分系统单元测试"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.recipes import evaluate_recipe, get_rating


class TestGetRating:
    def test_dark_cuisine(self):
        result = get_rating(0)
        assert result["name"] == "黑暗料理"

    def test_barely_drinkable(self):
        result = get_rating(20)
        assert result["name"] == "勉强能喝"

    def test_normal(self):
        result = get_rating(40)
        assert result["name"] == "普通奶茶"

    def test_good(self):
        result = get_rating(50)
        assert result["name"] == "好喝推荐"

    def test_popular(self):
        result = get_rating(65)
        assert result["name"] == "网红爆款"

    def test_craftsmanship(self):
        result = get_rating(80)
        assert result["name"] == "匠心之作"

    def test_michelin_one_star(self):
        result = get_rating(95)
        assert result["name"] == "米其林一星"

    def test_michelin_three_star(self):
        result = get_rating(100)
        assert result["name"] == "米其林三星"

    def test_above_max(self):
        result = get_rating(150)
        assert result["name"] == "米其林三星"


class TestEvaluateRecipe:
    def test_empty_ingredients(self):
        result = evaluate_recipe([])
        assert result["recipe_name"] == "空气奶茶"
        assert result["total_score"] == 0

    def test_classic_milk_tea(self):
        result = evaluate_recipe(["红茶", "牛奶"])
        assert result["recipe_name"] == "经典丝袜奶茶"
        assert result["score"] == 85

    def test_pearl_milk_tea(self):
        result = evaluate_recipe(["红茶", "牛奶", "珍珠"])
        assert result["recipe_name"] == "珍珠奶茶·祖师爷"
        assert result["score"] == 95

    def test_single_ingredient(self):
        result = evaluate_recipe(["红茶"])
        assert result["recipe_name"] == "孤傲红茶"
        assert result["score"] == 40

    def test_unknown_combination(self):
        result = evaluate_recipe(["红茶", "珍珠"])
        assert result["score"] == 80  # 珍珠红茶是已知配方

    def test_count_bonus(self):
        result = evaluate_recipe(["红茶", "牛奶", "珍珠"])
        count_bonus = min(3 * 3, 15)  # 3 个食材，每个 +3 分，最多 +15
        expected_total = min(95 + count_bonus, 120)
        assert result["total_score"] == expected_total

    def test_rating_tier(self):
        result = evaluate_recipe(["红茶", "牛奶", "珍珠"])
        assert result["rating"]["name"] in ["米其林一星", "米其林三星"]

    def test_all_ingredients(self):
        result = evaluate_recipe(["红茶", "牛奶", "珍珠", "椰果", "布丁", "仙草"])
        assert result["score"] == 100
        assert result["recipe_name"] == "奶茶界的满汉全席"
