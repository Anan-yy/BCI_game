"""BCI 信号滤波器单元测试"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bci.filter import (
    DeadZoneFilter,
    ExponentialSmoothing,
    SensitivityCurve,
    AttentionMappingCurve,
)


class TestDeadZoneFilter:
    def test_within_deadzone(self):
        f = DeadZoneFilter(threshold=5)
        assert f.filter(3) == 0
        assert f.filter(-3) == 0
        assert f.filter(0) == 0

    def test_outside_deadzone(self):
        f = DeadZoneFilter(threshold=5)
        assert f.filter(7) == 7
        assert f.filter(-7) == -7

    def test_at_threshold(self):
        f = DeadZoneFilter(threshold=5)
        assert f.filter(5) == 5
        assert f.filter(-5) == -5

    def test_custom_threshold(self):
        f = DeadZoneFilter(threshold=10)
        assert f.filter(8) == 0
        assert f.filter(12) == 12


class TestExponentialSmoothing:
    def test_first_value(self):
        s = ExponentialSmoothing(alpha=0.3)
        assert s.smooth(50) == 50

    def test_smoothing(self):
        s = ExponentialSmoothing(alpha=0.5)
        s.smooth(100)  # 初始化
        result = s.smooth(0)
        assert result == 50  # 0.5 * 0 + 0.5 * 100

    def test_multiple_smooths(self):
        s = ExponentialSmoothing(alpha=0.5)
        s.smooth(100)
        s.smooth(0)
        result = s.smooth(0)
        assert result == 25  # 0.5 * 0 + 0.5 * 50

    def test_alpha_one_no_smoothing(self):
        s = ExponentialSmoothing(alpha=1.0)
        s.smooth(100)
        assert s.smooth(50) == 50

    def test_alpha_zero_no_change(self):
        s = ExponentialSmoothing(alpha=0.0)
        s.smooth(100)
        assert s.smooth(50) == 100


class TestSensitivityCurve:
    def test_positive_input(self):
        sc = SensitivityCurve(base_sensitivity=1.0, exponent=2.0)
        assert sc.apply(2) == 4.0  # 2^2 = 4

    def test_negative_input(self):
        sc = SensitivityCurve(base_sensitivity=1.0, exponent=2.0)
        assert sc.apply(-2) == -4.0  # 保持符号

    def test_zero_input(self):
        sc = SensitivityCurve(base_sensitivity=1.0, exponent=2.0)
        assert sc.apply(0) == 0.0

    def test_custom_sensitivity(self):
        sc = SensitivityCurve(base_sensitivity=2.0, exponent=1.0)
        assert sc.apply(5) == 10.0  # 2 * 5^1 = 10


class TestAttentionMappingCurve:
    def test_low_attention(self):
        ac = AttentionMappingCurve()
        multiplier = ac.map_attention(0)
        assert multiplier == 0.5

    def test_low_attention_mid(self):
        ac = AttentionMappingCurve()
        multiplier = ac.map_attention(15)
        assert multiplier == 0.65  # 0.5 + (15/30) * 0.3

    def test_mid_attention(self):
        ac = AttentionMappingCurve()
        multiplier = ac.map_attention(50)
        assert multiplier == 0.9  # 0.8 + (20/40) * 0.2

    def test_high_attention(self):
        ac = AttentionMappingCurve()
        multiplier = ac.map_attention(100)
        assert multiplier == 1.5

    def test_boundary_low(self):
        ac = AttentionMappingCurve()
        assert ac.map_attention(30) == 0.8

    def test_boundary_high(self):
        ac = AttentionMappingCurve()
        assert ac.map_attention(70) == 1.0

    def test_clamp_min(self):
        ac = AttentionMappingCurve()
        assert ac.map_attention(-10) == 0.5  # 钳制到 0

    def test_clamp_max(self):
        ac = AttentionMappingCurve()
        assert ac.map_attention(150) == 1.5  # 钳制到 100

    def test_rating_tier_low(self):
        ac = AttentionMappingCurve()
        assert ac.get_rating_tier(20) == "分心状态"

    def test_rating_tier_mid(self):
        ac = AttentionMappingCurve()
        assert ac.get_rating_tier(50) == "平稳专注"

    def test_rating_tier_high(self):
        ac = AttentionMappingCurve()
        assert ac.get_rating_tier(80) == "高度专注"
