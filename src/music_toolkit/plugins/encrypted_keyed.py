"""需要密钥的格式占位插件。

框架不提供密钥输入入口，因此 ``key`` 实际上总是 ``None``；即使调用方
显式传入 key，也不会被使用，仍然只抛 ``UnsupportedFormat``。
"""

from __future__ import annotations

from pathlib import Path

from ..core.errors import MissingKey, UnsupportedFormat
from ..core.models import SupportLevel
from ..core.plugin_base import BasePlugin


class EncryptedKeyedPlugin(BasePlugin):
    """kgg 的占位实现。"""

    format_names = ("kgg",)
    support_level = SupportLevel.KEYED

    def convert(self, src: Path, dst: Path, cancel_event=None, key: bytes | None = None) -> None:
        if key is None:
            raise MissingKey("该格式需要密钥，当前框架不提供密钥输入入口")
        raise UnsupportedFormat("本框架不提供该格式的解密能力")


__all__ = ["EncryptedKeyedPlugin"]
