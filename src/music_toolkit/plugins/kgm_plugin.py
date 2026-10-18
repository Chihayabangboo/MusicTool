from pathlib import Path
from ..core.plugin_base import BasePlugin
from ..core.errors import UnsupportedFormat

class KgmPlugin(BasePlugin):
    format_names = ("kgm", "kgma", "vpr")
    support_level = "OFFLINE"

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        try:
            import libtakiyasha
        except ImportError:
            raise UnsupportedFormat("请先安装依赖: pip install libtakiyasha")

        try:
            from libtakiyasha.kgm import KGM
            file = KGM(str(src))
            with open(dst, "wb") as f:
                f.write(file.audio)
        except Exception as e:
            raise UnsupportedFormat(f"KGM 解析失败: {str(e)}")