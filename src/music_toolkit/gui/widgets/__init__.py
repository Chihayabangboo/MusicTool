"""GUI 可复用控件：带 job_id 的 Tableview 和简易 ToolTip。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Iterable

from ttkbootstrap.tableview import TableRow, Tableview


class JobTableview(Tableview):
    """Tableview 的薄封装。

    原生 ``Tableview.insert_row`` 不接受 ``iid``；这里补上该能力，
    让表格行主键直接使用 job_id，不额外增加隐藏列。
    """

    def insert_row(
        self,
        index="end",
        values: Iterable | None = None,
        iid: str | None = None,
        tags: Iterable[str] = (),
        reload: bool = False,
    ) -> TableRow | None:
        values = [] if values is None else list(values)
        if iid is None:
            row = super().insert_row(index=index, values=values)
            if row is not None and tags:
                self.view.item(row.iid, tags=tuple(tags))
            if reload:
                self.load_table_data()
            return row

        if not values:
            return None

        row = TableRow(self, values)
        row._iid = str(iid)
        self._tablerows.append(row)
        self._iidmap[row.iid] = row
        self.view.insert("", "end", iid=row.iid, values=row.values, tags=tuple(tags))
        if reload:
            self.load_table_data()
        return row

    def update_row(self, iid: str, values: Iterable) -> None:
        iid = str(iid)
        new_values = list(values)
        row = self._iidmap.get(iid)
        if row is not None:
            row._values = new_values
        if self.view.exists(iid):
            self.view.item(iid, values=new_values)

    def set_row_tags(self, iid: str, tags: Iterable[str]) -> None:
        iid = str(iid)
        if self.view.exists(iid):
            self.view.item(iid, tags=tuple(tags))

    def clear_all(self) -> None:
        children = self.view.get_children()
        if children:
            self.view.delete(*children)
        self._tablerows.clear()
        self._tablerows_filtered.clear()
        self._viewdata.clear()
        self._iidmap.clear()
        try:
            self.searchcriteria.set("")
        except (AttributeError, tk.TclError):
            pass


class ToolTip:
    """轻量 ToolTip，不依赖额外第三方库。"""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 400) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self) -> None:
        if self._window is not None:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            window,
            text=self.text,
            justify="left",
            background="#ffffe0",
            foreground="#222222",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=3,
        )
        label.pack()
        self._window = window

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None


__all__ = ["JobTableview", "ToolTip"]
