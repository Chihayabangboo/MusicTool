from pathlib import Path
from ..core.plugin_base import BasePlugin
from ..core.errors import UnsupportedFormat

class QmcPlugin(BasePlugin):
    format_names = ("qmc0", "qmc3", "qmcflac", "qmcogg", "mflac", "mgg")
    support_level = "OFFLINE"

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        try:
            # 统一使用 libtakiyasha 库
            from libtakiyasha import qmc
        except ImportError:
            raise UnsupportedFormat("请先安装依赖: pip install libtakiyasha")

        try:
            # 自动判断是 QMCv1 还是 QMCv2
            file = qmc.QMC(str(src))
            with open(dst, "wb") as f:
                f.write(file.audio)
        except Exception as e:
            raise UnsupportedFormat(f"QMC 解析失败(可能需要密钥): {str(e)}")