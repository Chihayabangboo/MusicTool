"""纯逻辑层：不依赖任何 GUI 库。"""

from __future__ import annotations

from .errors import (
    DecryptFailed,
    FfmpegNotFound,
    MissingKey,
    MusicToolkitError,
    TranscodeFailed,
    UnsupportedFormat,
)
from .models import Job, JobStatus, ScanItem, ScanResult, SupportLevel

__all__ = [
    "DecryptFailed",
    "FfmpegNotFound",
    "Job",
    "JobStatus",
    "MissingKey",
    "MusicToolkitError",
    "ScanItem",
    "ScanResult",
    "SupportLevel",
    "TranscodeFailed",
    "UnsupportedFormat",
]
