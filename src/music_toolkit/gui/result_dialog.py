"""GUI 结果弹窗。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk as tkttk

import ttkbootstrap as ttk


class ResultDialog(ttk.Toplevel):
    """转换结果对话框：统计、可折叠失败列表、打开输出目录。"""

    def __init__(
        self,
        master,
        total: int,
        success: int,
        failed: int,
        failures: list[tuple[str, str]] | None = None,
        on_open_dir=None,
        output_dir: str | Path | None = None,
    ) -> None:
        super().__init__(master)
        self.title("转换结果")
        self.geometry("620x430")
        self.minsize(520, 320)
        self.transient(master)
        self.grab_set()

        self.total = total
        self.success = success
        self.failed = failed
        self.failures = list(failures or [])
        self.on_open_dir = on_open_dir
        self.output_dir = Path(output_dir) if output_dir else None
        self._failure_paths: dict[str, str] = {}
        self._expanded = False
        self._failure_frame: ttk.Frame | None = None
        self._failure_tree: tkttk.Treeview | None = None
        self._toggle_button: ttk.Button | None = None

        self._build()
        if self.failures:
            self._set_expanded(True)

    def _build(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=f"总计：{self.total}", font=("", 12, "bold")).pack(
            anchor="w", pady=(0, 6)
        )
        ttk.Label(
            container,
            text=f"成功：{self.success}",
            foreground="#2ecc71",
            font=("", 11, "bold"),
        ).pack(anchor="w", pady=2)
        ttk.Label(
            container,
            text=f"失败：{self.failed}",
            foreground="#e74c3c",
            font=("", 11, "bold"),
        ).pack(anchor="w", pady=2)

        self._toggle_button = ttk.Button(
            container,
            text=self._toggle_text(),
            bootstyle="link",
            command=self._toggle,
            state="normal" if self.failed else "disabled",
        )
        self._toggle_button.pack(anchor="w", pady=(8, 4))

        self._failure_frame = ttk.Frame(container)
        columns = ("file", "reason")
        tree = tkttk.Treeview(
            self._failure_frame,
            columns=columns,
            show="headings",
            height=8,
        )
        tree.heading("file", text="文件名")
        tree.heading("reason", text="失败原因")
        tree.column("file", width=210, anchor="w")
        tree.column("reason", width=340, anchor="w")
        scrollbar = ttk.Scrollbar(self._failure_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for filename, reason in self.failures:
            display = Path(str(filename)).name or str(filename)
            row_id = tree.insert("", "end", values=(display, reason))
            self._failure_paths[row_id] = str(filename)
        tree.bind("<Double-1>", self._show_failure_detail)
        self._failure_tree = tree

        buttons = ttk.Frame(container)
        buttons.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Button(
            buttons,
            text="打开输出目录",
            bootstyle="secondary",
            command=self._open_output_dir,
        ).pack(side="left")
        ttk.Button(buttons, text="关闭", bootstyle="primary", command=self.destroy).pack(
            side="right"
        )

    def _toggle_text(self) -> str:
        if self._expanded:
            return f"▾ 收起失败文件（{self.failed}）"
        return f"▸ 查看失败文件（{self.failed}）"

    def _toggle(self) -> None:
        if not self.failed:
            return
        self._set_expanded(not self._expanded)

    def _set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        if self._failure_frame is None:
            return
        if expanded:
            self._failure_frame.pack(fill="both", expand=True, pady=(4, 0))
        else:
            self._failure_frame.pack_forget()
        if self._toggle_button is not None:
            self._toggle_button.configure(text=self._toggle_text())

    def _show_failure_detail(self, _event=None) -> None:
        if self._failure_tree is None:
            return
        selection = self._failure_tree.selection()
        if not selection:
            return
        values = self._failure_tree.item(selection[0], "values")
        if not values:
            return
        filename, reason = values[0], values[1]
        full_path = self._failure_paths.get(selection[0], filename)
        messagebox.showerror("失败详情", f"{full_path}\n\n{reason}", parent=self)

    def _open_output_dir(self) -> None:
        if self.on_open_dir is not None:
            self.on_open_dir()
            return
        if self.output_dir is None:
            return
        path = str(self.output_dir)
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)


__all__ = ["ResultDialog"]
