"""仅识别格式占位插件。"""

from __future__ import annotations

from pathlib import Path

from ..core.errors import UnsupportedFormat
from ..core.models import SupportLevel
from ..core.plugin_base import BasePlugin


class EncryptedDetectOnlyPlugin(BasePlugin):
    """qmc3（mgg1/mgg2/mmp4）的占位实现。"""

    format_names = ("qmc3",)
    support_level = SupportLevel.DETECT_ONLY

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        raise UnsupportedFormat("该格式仅支持识别，本框架不提供转换能力")


__all__ = ["EncryptedDetectOnlyPlugin"]
