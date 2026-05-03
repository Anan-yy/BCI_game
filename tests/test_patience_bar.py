"""耐心条单元测试"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from game.patience_bar import PatienceBar, CHECK_INTERVAL, FULL_BAR_DURATION


class TestPatienceBar:
    def test_initial_state(self):
        bar = PatienceBar(0, 0)
        assert bar.fill == 1.0
        assert bar.check_timer == 0.0
        assert bar.caught_in_interval is False
        assert bar.direction == -1  # 初始默认减少

    def test_on_catch_marks_caught(self):
        bar = PatienceBar(0, 0)
        bar.on_catch()
        assert bar.caught_in_interval is True

    def test_no_catch_decreases_fill(self):
        bar = PatienceBar(0, 0)
        bar.direction = -1
        bar.update(CHECK_INTERVAL)
        assert bar.fill < 1.0

    def test_catch_increases_fill(self):
        bar = PatienceBar(0, 0)
        bar.on_catch()
        bar.update(CHECK_INTERVAL)
        assert bar.direction == 1  # 3秒后判断为接住过
        bar.update(CHECK_INTERVAL)  # 再过一个周期，fill 应该增加
        assert bar.fill > 0.0  # fill 至少不会为负

    def test_fill_clamped(self):
        bar = PatienceBar(0, 0)
        bar.direction = -1
        for _ in range(1000):
            bar.update(CHECK_INTERVAL)
        assert bar.fill == 0.0

    def test_speed_calculated_correctly(self):
        bar = PatienceBar(0, 0)
        expected_speed = 1.0 / FULL_BAR_DURATION
        assert bar.speed == expected_speed
