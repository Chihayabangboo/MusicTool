"""GUI 后台线程辅助。

只负责创建线程和投递消息；worker 内部禁止直接操作 Tk 控件。
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from typing import Any


def start_worker(
    target: Callable[..., Any],
    *args: Any,
    name: str | None = None,
) -> threading.Thread:
    """创建并启动 daemon 线程。"""

    thread = threading.Thread(target=target, args=args, name=name, daemon=True)
    thread.start()
    return thread


def put_message(message_queue: queue.Queue, message: Any) -> None:
    """把消息放入 GUI 主线程消费的队列。"""

    message_queue.put(message)


__all__ = ["put_message", "start_worker"]
