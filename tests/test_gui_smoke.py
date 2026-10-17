from __future__ import annotations

import tkinter as tk
from pathlib import Path

import pytest


def test_gui_import_and_class():
    from music_toolkit.gui.main_window import MainWindow
    from music_toolkit.gui.result_dialog import ResultDialog

    assert issubclass(MainWindow, tk.Tk)
    assert issubclass(ResultDialog, tk.Toplevel)


def test_gui_smoke_three_seconds():
    """第十二节等级 1：创建窗口，3 秒后自动关闭。"""

    try:
        from music_toolkit.gui.main_window import MainWindow

        window = MainWindow()
    except tk.TclError as exc:
        pytest.skip(f"无可用显示环境，GUI 冒烟降级: {exc}")

    try:
        from music_toolkit.core.models import ScanItem, SupportLevel
        from music_toolkit.services.messages import (
            ScanBatchMsg,
            TaskOkMsg,
            TaskProgressMsg,
        )

        window._on_scan_batch(
            ScanBatchMsg(
                items=[
                    ScanItem(
                        path=Path("sample.wav"),
                        format="wav",
                        support_level=SupportLevel.OFFLINE,
                        input_root=None,
                    )
                ]
            )
        )
        assert window.table.view.exists("job-000001")
        assert window.table.view.item("job-000001", "values")[0] == "sample.wav"
        assert "OFFLINE" in window.table.view.item("job-000001", "tags")

        window._on_task_progress(
            TaskProgressMsg(job_id="job-000001", percent=50, overall_done=0, overall_total=1)
        )
        assert window.table.view.item("job-000001", "values")[3] == "转换中"
        window._on_task_ok(TaskOkMsg(job_id="job-000001", dst=Path("sample.mp3")))
        assert window.table.view.item("job-000001", "values")[3] == "成功"

        window.after(3000, window.destroy)
        window.mainloop()
    finally:
        try:
            window.destroy()
        except tk.TclError:
            pass
