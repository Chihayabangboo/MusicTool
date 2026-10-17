"""插件接口。插件是转换请求的唯一处理入口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

from .models import SupportLevel


class BasePlugin(ABC):
    """所有内置/第三方插件必须实现的接口。

    插件只负责自己声明的 ``format_names``，不得重复实现魔数识别，
    也不得跳过 TaskService 直接被 GUI 或 CLI 调用。
    """

    format_names: ClassVar[tuple[str, ...]] = ()
    support_level: ClassVar[SupportLevel] = SupportLevel.ERROR

    @abstractmethod
    def convert(
        self,
        src: Path,
        dst: Path,
        cancel_event=None,
        key: bytes | None = None,
    ) -> None:
        """把 ``src`` 处理为 ``dst``。

        - 普通音频插件调用 ``core.converter.run_ffmpeg``，忽略 ``key``。
        - 加密格式插件只保留占位：不支持时抛 ``UnsupportedFormat``，
          需要密钥时抛 ``MissingKey``。
        - 所有异常必须来自 ``core.errors``。
        """
        raise NotImplementedError
