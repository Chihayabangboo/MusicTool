"""框架数据模型与枚举。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SupportLevel(str, Enum):
    """格式支持级别。"""

    OFFLINE = "OFFLINE"
    KEYED = "KEYED"
    DETECT_ONLY = "DETECT_ONLY"
    ERROR = "ERROR"


class JobStatus(str, Enum):
    """单个转换任务状态。"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


@dataclass
class ScanItem:
    """扫描结果条目。"""

    path: Path
    format: str
    support_level: SupportLevel
    input_root: Path | None = None
    info: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class Job:
    """单个转换任务。"""

    id: str
    src: Path
    dst: Path | None = None
    input_root: Path | None = None
    status: JobStatus = JobStatus.PENDING
    error: str | None = None


@dataclass
class ScanResult:
    """扫描汇总。"""

    items: list[ScanItem] = field(default_factory=list)
    skipped: int = 0
    errors: int = 0
