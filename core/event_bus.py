"""事件总线 - 解耦组件间通信"""

import logging

logger = logging.getLogger(__name__)


class EventBus:
    """发布-订阅模式的事件总线

    使用方式:
        bus = EventBus()
        bus.on("score_changed", hud.update_score)
        bus.emit("score_changed", score=100, ingredient="红茶")
        bus.off("score_changed", hud.update_score)
    """

    def __init__(self):
        self._listeners = {}

    def on(self, event: str, callback):
        """订阅事件"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def off(self, event: str, callback):
        """取消订阅"""
        if event in self._listeners:
            self._listeners[event] = [cb for cb in self._listeners[event] if cb != callback]

    def emit(self, event: str, **kwargs):
        """发布事件，通知所有订阅者"""
        if event not in self._listeners:
            return
        for callback in self._listeners[event]:
            try:
                callback(**kwargs)
            except Exception as e:
                logger.error("事件处理失败 [%s]: %s", event, e)

    def clear(self):
        """清除所有订阅"""
        self._listeners.clear()
