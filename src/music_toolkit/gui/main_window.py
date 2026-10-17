"""GUI 主窗口。

线程模型：耗时任务全部在 ``threading.Thread`` 中执行；worker 只向
``queue.Queue`` 放入消息，主线程用 ``after(100)`` 轮询并更新控件。
"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

import ttkbootstrap as ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

from ..services.app_factory import bootstrap_app
from ..services.messages import (
    CancelledMsg,
    FinishedMsg,
    LogMsg,
    ScanBatchMsg,
    ScanDoneMsg,
    ScanStartMsg,
    TaskFailMsg,
    TaskOkMsg,
    TaskProgressMsg,
)
from ..services.task_service import make_job
from .log_handler import GuiLogHandler
from .result_dialog import ResultDialog
from .widgets import JobTableview, ToolTip
from .workers import start_worker

logger = logging.getLogger(__name__)

_LEVEL_COLORS = {
    "OFFLINE": "#2ecc71",
    "KEYED": "#f1c40f",
    "DETECT_ONLY": "#e67e22",
    "ERROR": "#e74c3c",
}

_STATUS_BY_LEVEL = {
    "OFFLINE": "排队中",
    "KEYED": "需要密钥",
    "DETECT_ONLY": "仅识别",
    "ERROR": "识别失败",
}

_COLUMNS = [
    {"text": "文件名", "width": 290, "stretch": True},
    {"text": "格式", "width": 100, "stretch": False},
    {"text": "支持级别", "width": 120, "stretch": False},
    {"text": "状态", "width": 100, "stretch": False},
    {"text": "进度", "width": 80, "stretch": False},
    {"text": "错误", "width": 260, "stretch": True},
]


class MainWindow(ttk.Window):
    """本地音乐格式识别与转换主窗口。"""

    def __init__(self) -> None:
        super().__init__(
            title="Music Toolkit — 本地音乐格式识别与转换",
            themename="superhero",
            size=(1100, 750),
        )
        self.minsize(900, 600)

        self._init_dnd()

        self.ctx = bootstrap_app()
        self.message_queue: queue.Queue = queue.Queue()
        self.jobs: dict[str, object] = {}
        self.job_paths: dict[str, Path] = {}
        self.job_levels: dict[str, str] = {}
        self.job_formats: dict[str, str] = {}
        self._job_counter = 0
        self._seen_keys: set[str] = set()

        self._scanning = False
        self._running = False
        self._closing = False
        self._scan_cancel: threading.Event | None = None
        self._run_cancel: threading.Event | None = None
        self._poll_after_id: str | None = None
        self._failed_entries: list[tuple[str, str]] = []
        self._last_success = 0
        self._last_failed = 0

        self.output_dir_var = tk.StringVar(value="")
        self.format_var = tk.StringVar(value="MP3")
        self.recursive_var = tk.BooleanVar(value=False)
        self.keep_structure_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.count_var = tk.StringVar(value="已添加：0")
        self.status_var = tk.StringVar(value="就绪")
        self.detail_var = tk.StringVar(value="选中文件可查看元数据")
        self.progress_text_var = tk.StringVar(value="总进度 0%")

        self._build_ui()
        self._install_log_handler()
        self._refresh_start_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<F5>", lambda _event: self._on_start())
        self.bind("<Escape>", lambda _event: self._on_cancel())
        self._poll_after_id = self.after(100, self._poll_queue)

    # ------------------------------------------------------------------ DnD
    def _init_dnd(self) -> None:
        try:
            try:
                TkinterDnD._require(self)
            except AttributeError:
                import tkinterdnd2

                tkinterdnd2._require(self)
            self._dnd_available = True
        except Exception as exc:  # 拖拽不可用时仍可正常启动
            logger.warning("拖拽功能初始化失败: %s", exc)
            self._dnd_available = False

    def _bind_drop(self, widget) -> None:
        if not getattr(self, "_dnd_available", False):
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)
        except Exception as exc:
            logger.warning("注册拖拽目标失败: %s", exc)

    def _on_drop(self, event):
        try:
            paths = [Path(item) for item in self.tk.splitlist(event.data)]
        except (tk.TclError, ValueError) as exc:
            logger.warning("无法解析拖拽路径: %s", exc)
            return getattr(event, "action", None)
        self._add_paths(paths)
        return getattr(event, "action", None)

    # ------------------------------------------------------------- interface
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=3)
        self.rowconfigure(4, weight=1)

        toolbar = ttk.Frame(self, padding=(12, 10, 12, 4))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(0, weight=1)
        self._bind_drop(toolbar)

        actions = ttk.Frame(toolbar)
        actions.grid(row=0, column=0, sticky="ew")
        self.add_file_btn = ttk.Button(
            actions, text="添加文件", bootstyle="primary-outline", command=self._add_files
        )
        self.add_file_btn.pack(side="left", padx=(0, 6))
        self.add_folder_btn = ttk.Button(
            actions, text="添加文件夹", bootstyle="primary-outline", command=self._add_folder
        )
        self.add_folder_btn.pack(side="left", padx=(0, 6))
        self.clear_btn = ttk.Button(
            actions, text="清空", bootstyle="secondary-outline", command=self._clear
        )
        self.clear_btn.pack(side="left", padx=(0, 12))
        ttk.Checkbutton(
            actions,
            text="包含子文件夹",
            variable=self.recursive_var,
            bootstyle="round-toggle",
        ).pack(side="left", padx=(0, 14))
        ttk.Label(actions, textvariable=self.count_var).pack(side="left")

        self.start_btn = ttk.Button(
            actions,
            text="▶ 开始转换",
            bootstyle="success",
            command=self._on_start,
            state="disabled",
        )
        self.start_btn.pack(side="right", padx=(6, 0))
        self.cancel_btn = ttk.Button(
            actions,
            text="■ 取消",
            bootstyle="danger-outline",
            command=self._on_cancel,
            state="disabled",
        )
        self.cancel_btn.pack(side="right")

        output_row = ttk.Frame(toolbar)
        output_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        output_row.columnconfigure(1, weight=1)
        ttk.Label(output_row, text="输出目录：").grid(row=0, column=0, sticky="w")
        self.output_entry = ttk.Entry(
            output_row,
            textvariable=self.output_dir_var,
            state="readonly",
        )
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.folder_btn = ttk.Button(
            output_row,
            text="📁",
            width=3,
            bootstyle="secondary-outline",
            command=self._choose_output_dir,
        )
        self.folder_btn.grid(row=0, column=2, padx=(0, 18))
        self.folder_tooltip = ToolTip(self.folder_btn, "选择输出目录")

        ttk.Label(output_row, text="输出格式：").grid(row=0, column=3, sticky="w")
        self.format_combo = ttk.Combobox(
            output_row,
            textvariable=self.format_var,
            values=["MP3", "FLAC", "WAV", "OGG"],
            state="readonly",
            width=8,
        )
        self.format_combo.grid(row=0, column=4, sticky="w")

        options_row = ttk.Frame(toolbar)
        options_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(
            options_row,
            text="保留子文件夹结构",
            variable=self.keep_structure_var,
            bootstyle="round-toggle",
        ).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(
            options_row,
            text="覆盖已存在文件",
            variable=self.overwrite_var,
            bootstyle="round-toggle",
        ).pack(side="left")
        ttk.Label(
            options_row,
            textvariable=self.status_var,
            bootstyle="inverse-secondary",
        ).pack(side="right")

        table_frame = ttk.Frame(self, padding=(12, 4))
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self._bind_drop(table_frame)

        self.table = JobTableview(
            master=table_frame,
            coldata=_COLUMNS,
            searchable=True,
            stripecolor=("#25313a", None),
            height=13,
        )
        self.table.grid(row=0, column=0, sticky="nsew")
        for level, color in _LEVEL_COLORS.items():
            self.table.view.tag_configure(level, foreground=color)
        for index in range(len(_COLUMNS)):
            self.table.view.heading(
                index,
                command=lambda i=index: self.table.sort_column_data(cid=str(i)),
            )
        self.table.view.bind("<<TreeviewSelect>>", self._on_select_row)
        self._bind_drop(self.table)

        detail = ttk.Label(
            self,
            textvariable=self.detail_var,
            bootstyle="secondary",
            padding=(12, 2, 12, 2),
            anchor="w",
        )
        detail.grid(row=2, column=0, sticky="ew")

        self.progress = ttk.Floodgauge(
            self,
            maximum=100,
            value=0,
            text="总进度 0%",
            bootstyle="success",
        )
        self.progress.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 6))

        log_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        log_frame.grid(row=4, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)
        ttk.Label(log_frame, text="运行日志").grid(row=0, column=0, sticky="w")
        self.log_text = ScrolledText(
            log_frame,
            height=6,
            wrap="word",
            state="disabled",
            background="#10171e",
            foreground="#d7e2ea",
            insertbackground="#d7e2ea",
            relief="flat",
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        self.output_dir_var.trace_add("write", lambda *_: self._refresh_start_state())
        self.format_var.trace_add("write", lambda *_: self._refresh_start_state())

    def _install_log_handler(self) -> None:
        self.log_handler = GuiLogHandler(self.message_queue)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S")
        )
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(self.log_handler)

    # --------------------------------------------------------------- actions
    def _add_files(self) -> None:
        if self._scanning or self._running:
            return
        selected = filedialog.askopenfilenames(
            title="选择音乐文件",
            filetypes=[
                (
                    "音频文件",
                    "*.wav *.flac *.mp3 *.ogg *.ncm *.qmc* *.mflac *.mgg "
                    "*.kgm *.kgma *.vpr *.kgg *.kwm",
                ),
                ("所有文件", "*.*"),
            ],
        )
        if selected:
            self._add_paths([Path(path) for path in selected])

    def _add_folder(self) -> None:
        if self._scanning or self._running:
            return
        selected = filedialog.askdirectory(title="选择音乐文件夹")
        if selected:
            self._add_paths([Path(selected)])

    def _add_paths(self, paths: list[Path]) -> None:
        if self._running or self._scanning:
            return
        existing = {str(path.resolve()).lower() for path in paths if path.exists()}
        if not existing:
            return
        self._start_scan(paths)

    def _start_scan(self, paths: list[Path]) -> None:
        self._scanning = True
        self._scan_cancel = threading.Event()
        self._set_add_buttons("disabled")
        self.status_var.set("正在扫描…")
        self.progress.configure(mode="indeterminate", value=0, text="正在扫描…")
        self.progress.start(15)
        recursive = self.recursive_var.get()
        start_worker(
            self._scan_worker,
            paths,
            recursive,
            self._scan_cancel,
            name="music-toolkit-scan",
        )

    def _scan_worker(
        self, paths: list[Path], recursive: bool, cancel_event: threading.Event
    ) -> None:
        try:
            entries = self.ctx.scan_service.expand(
                paths,
                recursive=recursive,
                suffix_filter=None,
                cancel_event=cancel_event,
            )
            self.message_queue.put(ScanStartMsg(total_hint=len(entries)))
            batch = []
            skipped = 0
            errors = 0
            for item in self.ctx.scan_service.iter_scan(
                entries, cancel_event=cancel_event, with_metadata=False
            ):
                batch.append(item)
                level = item.support_level.value
                if level == "ERROR":
                    errors += 1
                elif level == "DETECT_ONLY":
                    skipped += 1
                if len(batch) >= 30:
                    self.message_queue.put(ScanBatchMsg(items=list(batch)))
                    batch = []
            if batch:
                self.message_queue.put(ScanBatchMsg(items=list(batch)))
            self.message_queue.put(ScanDoneMsg(total=len(entries), skipped=skipped, errors=errors))
        except Exception as exc:  # worker 不得把异常留成静默死线程
            logger.exception("扫描失败")
            self.message_queue.put(ScanDoneMsg(total=0, skipped=0, errors=1))
            self.message_queue.put(LogMsg(level="ERROR", text=f"扫描失败: {exc}"))

    def _set_add_buttons(self, state: str) -> None:
        for button in (self.add_file_btn, self.add_folder_btn, self.clear_btn):
            button.configure(state=state)

    def _clear(self) -> None:
        if self._running or self._scanning:
            return
        self.table.clear_all()
        self.jobs.clear()
        self.job_paths.clear()
        self.job_levels.clear()
        self.job_formats.clear()
        self._seen_keys.clear()
        self._failed_entries.clear()
        self.count_var.set("已添加：0")
        self.status_var.set("就绪")
        self.detail_var.set("选中文件可查看元数据")
        self.progress.configure(mode="determinate", value=0, text="总进度 0%")
        self._refresh_start_state()

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="选择输出目录")
        if selected:
            self.output_dir_var.set(selected)
            self._refresh_start_state()

    def _output_dir(self) -> Path | None:
        value = self.output_dir_var.get().strip()
        return Path(value) if value else None

    def _output_dir_writable(self) -> bool:
        directory = self._output_dir()
        if directory is None or not directory.is_dir():
            return False
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".music-toolkit-write-", dir=directory, delete=True
            ) as handle:
                handle.write(b"ok")
            return True
        except OSError:
            return False

    def _refresh_start_state(self) -> None:
        if not hasattr(self, "start_btn"):
            return
        if self._running or self._scanning:
            self.start_btn.configure(state="disabled")
            return
        has_offline = any(
            self.job_levels.get(job_id) == "OFFLINE" and job.status.value == "PENDING"
            for job_id, job in self.jobs.items()
        )
        enabled = has_offline and self._output_dir() is not None and self._output_dir_writable()
        self.start_btn.configure(state="normal" if enabled else "disabled")

    def _validate_output_dir(self) -> Path | None:
        directory = self._output_dir()
        if directory is None:
            messagebox.showwarning("输出目录", "请先选择输出目录。", parent=self)
            return None
        if not directory.is_dir():
            messagebox.showwarning("输出目录", "输出目录不存在，请重新选择。", parent=self)
            return None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix=".music-toolkit-write-", dir=directory, delete=True
            ) as handle:
                handle.write(b"ok")
        except OSError as exc:
            messagebox.showerror("输出目录", f"输出目录不可写：{exc}", parent=self)
            return None
        return directory

    # ------------------------------------------------------------------ start
    def _on_start(self) -> None:
        if self._running or self._scanning:
            return
        output_dir = self._validate_output_dir()
        if output_dir is None:
            return

        pending = [job for job in self.jobs.values() if job.status.value == "PENDING"]
        offline = [job for job in pending if self.job_levels.get(job.id) == "OFFLINE"]
        if not pending:
            messagebox.showinfo("没有任务", "当前没有待处理文件，请先添加文件。", parent=self)
            return
        if not offline:
            messagebox.showwarning(
                "没有可转换文件",
                "当前没有 OFFLINE 级别的音频文件；加密格式仅做识别/级别判定。",
                parent=self,
            )
            return

        skipped = len(pending) - len(offline)
        if not messagebox.askyesno(
            "确认转换",
            f"将转换 {len(offline)} 个文件，跳过 {skipped} 个文件。\n\n继续？",
            parent=self,
        ):
            return

        self._running = True
        self._run_cancel = threading.Event()
        self._failed_entries = []
        self._last_success = 0
        self._last_failed = 0
        self.cancel_btn.configure(state="normal")
        self.start_btn.configure(state="disabled", text="⏳ 转换中…")
        self._set_add_buttons("disabled")
        self.status_var.set("正在转换…")
        self.progress.configure(mode="determinate", maximum=len(pending), value=0)
        self.progress_text_var.set(f"总进度 0/{len(pending)}")
        self.progress.configure(text=self.progress_text_var.get())

        target_ext = "." + self.format_var.get().strip().lower()
        planner = self.ctx.planner_factory(
            output_dir,
            target_ext,
            self.keep_structure_var.get(),
            self.overwrite_var.get(),
        )
        start_worker(
            self._convert_worker,
            pending,
            planner,
            self._run_cancel,
            name="music-toolkit-convert",
        )

    def _convert_worker(self, jobs, planner, cancel_event: threading.Event) -> None:
        state = {"done": 0, "total": len(jobs), "success": 0, "failed": 0}

        def on_task_progress(job_id: str, percent: int) -> None:
            self.message_queue.put(
                TaskProgressMsg(
                    job_id=job_id,
                    percent=percent,
                    overall_done=state["done"],
                    overall_total=state["total"],
                )
            )

        def on_overall_progress(done: int, total: int) -> None:
            state["done"] = done
            state["total"] = total

        def on_done(job_id: str, success: bool, dst_or_empty: str, error: str) -> None:
            if success:
                state["success"] += 1
                self.message_queue.put(TaskOkMsg(job_id=job_id, dst=Path(dst_or_empty)))
            else:
                state["failed"] += 1
                self.message_queue.put(TaskFailMsg(job_id=job_id, error=error))

        try:
            self.ctx.task_service.run_batch(
                jobs,
                planner,
                on_task_progress=on_task_progress,
                on_overall_progress=on_overall_progress,
                on_done=on_done,
                cancel_event=cancel_event,
            )
        except Exception as exc:  # 防止 worker 静默退出
            logger.exception("转换调度异常")
            self.message_queue.put(LogMsg(level="ERROR", text=f"转换调度异常: {exc}"))

        if cancel_event.is_set():
            self.message_queue.put(CancelledMsg(completed=state["success"] + state["failed"]))
        else:
            self.message_queue.put(
                FinishedMsg(
                    total=state["total"],
                    success=state["success"],
                    failed=state["failed"],
                )
            )

    def _on_cancel(self) -> None:
        if not self._running or self._run_cancel is None:
            return
        self._run_cancel.set()
        self.cancel_btn.configure(state="disabled")
        self.status_var.set("正在取消…")
        logger.info("用户请求取消转换")

    def _finish_run(self) -> None:
        self._running = False
        self._run_cancel = None
        self.cancel_btn.configure(state="disabled")
        self.start_btn.configure(text="▶ 开始转换")
        self._set_add_buttons("normal")
        self._refresh_start_state()

    def _on_finished(self, message: FinishedMsg) -> None:
        self._finish_run()
        self.progress.configure(
            mode="determinate", maximum=max(message.total, 1), value=message.total
        )
        self.progress.configure(text=f"总进度 {message.total}/{message.total}")
        self.status_var.set(f"完成：成功 {message.success}，失败 {message.failed}")
        self._open_result_dialog(message.total, message.success, message.failed)

    def _on_cancelled(self, message: CancelledMsg) -> None:
        self._finish_run()
        self.status_var.set(f"已取消，已完成 {message.completed} 个文件")
        self.progress.configure(text=f"已取消，已完成 {message.completed} 个文件")
        self._open_result_dialog(message.completed, self._last_success, self._last_failed)

    def _open_result_dialog(self, total: int, success: int, failed: int) -> None:
        ResultDialog(
            self,
            total=total,
            success=success,
            failed=failed,
            failures=list(self._failed_entries),
            on_open_dir=self._open_output_dir,
            output_dir=self._output_dir(),
        )

    def _open_output_dir(self) -> None:
        directory = self._output_dir()
        if directory is None or not directory.is_dir():
            return
        path = str(directory)
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc), parent=self)

    # --------------------------------------------------------------- messages
    def _poll_queue(self) -> None:
        if self._closing:
            return
        try:
            while True:
                message = self.message_queue.get_nowait()
                self._dispatch(message)
        except queue.Empty:
            pass
        self._poll_after_id = self.after(100, self._poll_queue)

    def _dispatch(self, message) -> None:
        if isinstance(message, ScanStartMsg):
            self._on_scan_start(message)
        elif isinstance(message, ScanBatchMsg):
            self._on_scan_batch(message)
        elif isinstance(message, ScanDoneMsg):
            self._on_scan_done(message)
        elif isinstance(message, TaskProgressMsg):
            self._on_task_progress(message)
        elif isinstance(message, TaskOkMsg):
            self._on_task_ok(message)
        elif isinstance(message, TaskFailMsg):
            self._on_task_fail(message)
        elif isinstance(message, FinishedMsg):
            self._on_finished(message)
        elif isinstance(message, CancelledMsg):
            self._on_cancelled(message)
        elif isinstance(message, LogMsg):
            self._append_log(message)
        else:
            logger.warning("收到未知消息类型: %r", type(message))

    def _on_scan_start(self, message: ScanStartMsg) -> None:
        self.status_var.set(f"正在扫描，预计 {message.total_hint} 个文件…")

    def _on_scan_batch(self, message: ScanBatchMsg) -> None:
        inserted = 0
        for item in message.items:
            root_key = str(item.input_root).lower() if item.input_root else ""
            key = f"{str(item.path).lower()}|{root_key}"
            if key in self._seen_keys:
                continue
            self._seen_keys.add(key)
            self._job_counter += 1
            job_id = f"job-{self._job_counter:06d}"
            job = make_job(job_id, item.path, item.input_root)
            self.jobs[job_id] = job
            self.job_paths[job_id] = item.path
            self.job_levels[job_id] = item.support_level.value
            self.job_formats[job_id] = item.format
            status = _STATUS_BY_LEVEL.get(item.support_level.value, "未知")
            values = [
                item.path.name,
                item.format.upper(),
                item.support_level.value,
                status,
                "0%",
                item.error or "",
            ]
            self.table.insert_row(values=values, iid=job_id, tags=(item.support_level.value,))
            inserted += 1
        if inserted:
            self.table.load_table_data()
        self.count_var.set(f"已添加：{len(self.jobs)}")

    def _on_scan_done(self, message: ScanDoneMsg) -> None:
        self._scanning = False
        self._scan_cancel = None
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        self.progress.configure(mode="determinate", value=0, text="总进度 0%")
        self._set_add_buttons("normal")
        self.count_var.set(f"已添加：{len(self.jobs)}")
        self.status_var.set(
            f"扫描完成：{message.total} 个文件，跳过 {message.skipped}，错误 {message.errors}"
        )
        try:
            self.table.autofit_columns()
        except Exception as exc:  # 布局问题不应阻塞使用
            logger.warning("自动调整列宽失败: %s", exc)
        self._refresh_start_state()

    def _on_task_progress(self, message: TaskProgressMsg) -> None:
        self._update_row(
            message.job_id,
            status="转换中" if message.percent < 100 else "完成",
            progress=f"{message.percent}%",
        )
        total = max(message.overall_total, 1)
        self.progress.configure(mode="determinate", maximum=total, value=message.overall_done)
        text = f"总进度 {message.overall_done}/{message.overall_total}"
        self.progress.configure(text=text)
        self.progress_text_var.set(text)

    def _on_task_ok(self, message: TaskOkMsg) -> None:
        self._last_success += 1
        self._update_row(message.job_id, status="成功", progress="100%", error="")

    def _on_task_fail(self, message: TaskFailMsg) -> None:
        self._last_failed += 1
        level = self.job_levels.get(message.job_id)
        status = "跳过" if level == "DETECT_ONLY" else "失败"
        self._update_row(message.job_id, status=status, progress="", error=message.error)
        path = self.job_paths.get(message.job_id)
        job = self.jobs.get(message.job_id)
        target = getattr(job, "dst", None)
        full_path = str(target or path or message.job_id)
        self._failed_entries.append((full_path, message.error))

    def _update_row(self, job_id: str, **changes) -> None:
        if job_id not in self.jobs:
            return
        current = list(self._row_values(job_id))
        mapping = {"status": 3, "progress": 4, "error": 5}
        for name, value in changes.items():
            index = mapping.get(name)
            if index is not None:
                current[index] = value
        self.table.update_row(job_id, current)

    def _row_values(self, job_id: str) -> tuple:
        if self.table.view.exists(job_id):
            values = self.table.view.item(job_id, "values")
            if values:
                return tuple(values)
        path = self.job_paths.get(job_id)
        return (
            path.name if path else "",
            self.job_formats.get(job_id, "").upper(),
            self.job_levels.get(job_id, ""),
            "",
            "",
            "",
        )

    def _append_log(self, message: LogMsg) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_select_row(self, _event=None) -> None:
        selection = self.table.view.selection()
        if not selection:
            self.detail_var.set("选中文件可查看元数据")
            return
        job_id = selection[0]
        path = self.job_paths.get(job_id)
        if path is None:
            return
        metadata = self.ctx.metadata_service.read_metadata(path)
        parts = [path.name]
        if "duration" in metadata:
            try:
                parts.append(f"时长 {float(metadata['duration']):.2f}s")
            except (TypeError, ValueError):
                pass
        if "bitrate" in metadata:
            try:
                parts.append(f"码率 {int(metadata['bitrate']) // 1000} kbps")
            except (TypeError, ValueError):
                pass
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), dict) else {}
        for key in ("title", "artist", "album", "TIT2", "TPE1", "TALB"):
            value = tags.get(key) if tags else None
            if value:
                parts.append(f"{key}={value}")
                break
        if len(parts) == 1:
            parts.append("无可用元数据")
        self.detail_var.set("   |   ".join(parts))

    # ------------------------------------------------------------------ close
    def _on_close(self) -> None:
        if self._running:
            if not messagebox.askyesno(
                "确认退出", "转换正在进行，确定要退出吗？", parent=self
            ):
                return
            if self._run_cancel is not None:
                self._run_cancel.set()
        self.destroy()

    def destroy(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self._poll_after_id is not None:
            try:
                self.after_cancel(self._poll_after_id)
            except tk.TclError:
                pass
            self._poll_after_id = None
        if self._scan_cancel is not None:
            self._scan_cancel.set()
        if self._run_cancel is not None:
            self._run_cancel.set()
        try:
            logging.getLogger().removeHandler(self.log_handler)
        except Exception:
            pass
        try:
            super().destroy()
        except tk.TclError:
            pass


__all__ = ["MainWindow"]
