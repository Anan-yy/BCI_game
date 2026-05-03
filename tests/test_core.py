"""AssetManager 和 EventBus 单元测试"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.event_bus import EventBus


class TestEventBus:
    def test_subscribe_and_emit(self):
        bus = EventBus()
        results = []
        bus.on("test_event", lambda value: results.append(value))
        bus.emit("test_event", value=42)
        assert results == [42]

    def test_multiple_listeners(self):
        bus = EventBus()
        results = []
        bus.on("score", lambda score: results.append(score))
        bus.on("score", lambda score: results.append(score * 2))
        bus.emit("score", score=10)
        assert results == [10, 20]

    def test_unsubscribe(self):
        bus = EventBus()
        results = []

        def cb():
            results.append(1)

        bus.on("evt", cb)
        bus.off("evt", cb)
        bus.emit("evt")
        assert results == []

    def test_emit_unknown_event(self):
        bus = EventBus()
        bus.emit("nonexistent")

    def test_listener_exception(self):
        bus = EventBus()
        bus.on("evt", lambda: 1 / 0)
        bus.on("evt", lambda: results.append("ok"))
        results = []
        bus.emit("evt")
        assert results == ["ok"]

    def test_clear(self):
        bus = EventBus()
        bus.on("evt", lambda: None)
        bus.clear()
        assert bus._listeners == {}
