"""GUI 与 worker 之间的消息协议。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..core.models import ScanItem


class MsgType(str, Enum):
    """消息类型。GUI 使用 ``isinstance`` 或 ``msg.type`` 分发。"""

    SCAN_START = "SCAN_START"
    SCAN_BATCH = "SCAN_BATCH"
    SCAN_DONE = "SCAN_DONE"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_OK = "TASK_OK"
    TASK_FAIL = "TASK_FAIL"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"
    LOG = "LOG"


@dataclass(frozen=True)
class ScanStartMsg:
    total_hint: int
    type: MsgType = field(default=MsgType.SCAN_START, init=False)


@dataclass(frozen=True)
class ScanBatchMsg:
    items: list[ScanItem]
    type: MsgType = field(default=MsgType.SCAN_BATCH, init=False)


@dataclass(frozen=True)
class ScanDoneMsg:
    total: int
    skipped: int
    errors: int
    type: MsgType = field(default=MsgType.SCAN_DONE, init=False)


@dataclass(frozen=True)
class TaskProgressMsg:
    job_id: str
    percent: int
    overall_done: int
    overall_total: int
    type: MsgType = field(default=MsgType.TASK_PROGRESS, init=False)


@dataclass(frozen=True)
class TaskOkMsg:
    job_id: str
    dst: Path
    type: MsgType = field(default=MsgType.TASK_OK, init=False)


@dataclass(frozen=True)
class TaskFailMsg:
    job_id: str
    error: str
    type: MsgType = field(default=MsgType.TASK_FAIL, init=False)


@dataclass(frozen=True)
class FinishedMsg:
    total: int
    success: int
    failed: int
    type: MsgType = field(default=MsgType.FINISHED, init=False)


@dataclass(frozen=True)
class CancelledMsg:
    completed: int
    type: MsgType = field(default=MsgType.CANCELLED, init=False)


@dataclass(frozen=True)
class LogMsg:
    level: str
    text: str
    type: MsgType = field(default=MsgType.LOG, init=False)


__all__ = [
    "CancelledMsg",
    "FinishedMsg",
    "LogMsg",
    "MsgType",
    "ScanBatchMsg",
    "ScanDoneMsg",
    "ScanStartMsg",
    "TaskFailMsg",
    "TaskOkMsg",
    "TaskProgressMsg",
]
