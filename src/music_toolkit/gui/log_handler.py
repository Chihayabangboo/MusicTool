"""GUI 日志处理器：把 logging 记录封装成 LogMsg 放进线程安全队列。"""

from __future__ import annotations

import logging
import queue

from ..services.messages import LogMsg


class GuiLogHandler(logging.Handler):
    """构造时传入 ``queue.Queue``；emit 只做入队，不操作 Tk 控件。"""

    def __init__(self, message_queue: queue.Queue) -> None:
        super().__init__()
        self.message_queue = message_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
        except Exception:  # noqa: BLE001 - logging 约定
            self.handleError(record)
            return
        self.message_queue.put(LogMsg(level=record.levelname, text=text))


__all__ = ["GuiLogHandler"]
