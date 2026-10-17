"""元数据服务：``core.metadata`` 的薄封装，GUI 和 CLI 通过它读取元数据。"""

from __future__ import annotations

from pathlib import Path

from ..core import metadata


class MetadataService:
    """供 GUI/CLI 使用的元数据读取入口。"""

    def read_metadata(self, path: str | Path) -> dict:
        return metadata.read(path)


def read_metadata(path: str | Path) -> dict:
    """模块级便捷函数，行为与 :meth:`MetadataService.read_metadata` 一致。"""

    return MetadataService().read_metadata(path)


__all__ = ["MetadataService", "read_metadata"]
