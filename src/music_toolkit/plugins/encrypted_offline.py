"""加密离线格式插件。"""
from __future__ import annotations

from pathlib import Path

from ..core.errors import UnsupportedFormat
from ..core.models import SupportLevel
from ..core.plugin_base import BasePlugin

_MESSAGE = "本框架不提供该格式的解密能力"


class EncryptedOfflinePlugin(BasePlugin):
    """ncm/qmc1/qmc2/kgm/kgma/vpr/kwm 的处理实现。"""

    format_names = ("ncm", "qmc1", "qmc2", "kgm", "kgma", "vpr", "kwm")
    support_level = SupportLevel.OFFLINE

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        import tempfile
        import os
        from ..core.converter import run_ffmpeg

        if src.suffix.lower() == ".ncm":
            try:
                from ncmdump import NeteaseCloudMusicFile
            except ImportError:
                raise UnsupportedFormat("请先安装解密依赖: pip install ncmdump-py")

            temp_path = None
            try:
                ncm = NeteaseCloudMusicFile(str(src))
                ncm.decrypt()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                    temp_path = tmp.name
                    
                ncm.dump_music(temp_path)
                
                run_ffmpeg(Path(temp_path), dst, cancel_event)
                
            except Exception as e:
                raise UnsupportedFormat(f"NCM 解析失败: {str(e)}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            raise UnsupportedFormat(_MESSAGE)


__all__ = ["EncryptedOfflinePlugin"]