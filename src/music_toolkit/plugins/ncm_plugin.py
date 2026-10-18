from pathlib import Path
from ..core.plugin_base import BasePlugin
from ..core.errors import UnsupportedFormat

class NcmPlugin(BasePlugin):
    format_names = ("ncm",)
    support_level = "OFFLINE"

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        try:
            from ncmdump import NeteaseCloudMusicFile
        except ImportError:
            raise UnsupportedFormat("请先安装依赖: pip install ncmdump-py")

        try:
            ncm = NeteaseCloudMusicFile(str(src))
            ncm.decrypt()
            ncm.dump_music(str(dst))
        except Exception as e:
            raise UnsupportedFormat(f"NCM 解析失败: {str(e)}")