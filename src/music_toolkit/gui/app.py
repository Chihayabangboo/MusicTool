"""GUI 启动入口。"""

from __future__ import annotations

import logging
import os
import tkinter as tk

logger = logging.getLogger(__name__)


def main() -> None:
    """创建主窗口并进入事件循环。"""

    try:
        from .main_window import MainWindow

        window = MainWindow()
        auto_close_ms = os.environ.get("MUSIC_TOOLKIT_AUTO_CLOSE_MS")
        if auto_close_ms:
            try:
                window.after(int(auto_close_ms), window.destroy)
            except ValueError:
                logger.warning("MUSIC_TOOLKIT_AUTO_CLOSE_MS 不是整数: %s", auto_close_ms)
        window.mainloop()
    except tk.TclError as exc:
        logger.error("无法启动 GUI（可能没有可用显示环境）: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
