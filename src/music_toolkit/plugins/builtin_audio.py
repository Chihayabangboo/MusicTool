"""普通音频插件：唯一会实际调用 ffmpeg 的插件。"""

from __future__ import annotations

import logging
from pathlib import Path

from ..core import converter
from ..core.models import SupportLevel
from ..core.plugin_base import BasePlugin

logger = logging.getLogger(__name__)


class BuiltinAudioPlugin(BasePlugin):
    """处理 wav/flac/mp3/ogg 的离线转码。"""

    format_names = ("wav", "flac", "mp3", "ogg")
    support_level = SupportLevel.OFFLINE

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        # key 对本插件无意义，按接口约定忽略。
        logger.info("开始转码 %s -> %s", src, dst)
        converter.run_ffmpeg(src, dst, cancel_event=cancel_event)


__all__ = ["BuiltinAudioPlugin"]
