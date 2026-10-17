"""输入展开与扫描服务。"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator, Iterable, Sequence
from pathlib import Path
from typing import TypeAlias

from ..core.detector import Detector
from ..core.models import ScanItem, SupportLevel
from .metadata_service import MetadataService

logger = logging.getLogger(__name__)

#: ``(绝对文件路径, 输入根目录)``；单文件输入的根目录为 ``None``。
ExpandedFile: TypeAlias = tuple[Path, Path | None]


def _normalize_filter(suffix_filter: Iterable[str] | None) -> set[str] | None:
    if suffix_filter is None:
        return None
    normalized: set[str] = set()
    for suffix in suffix_filter:
        value = suffix.strip().lower()
        if not value:
            continue
        normalized.add(value if value.startswith(".") else "." + value)
    return normalized or None


def _matches_filter(path: Path, suffix_filter: set[str] | None) -> bool:
    return suffix_filter is None or path.suffix.lower() in suffix_filter


class ScanService:
    """展开输入并识别文件；不执行转码。"""

    def __init__(self, detector: Detector, metadata_service: MetadataService | None = None) -> None:
        self.detector = detector
        self.metadata_service = metadata_service or MetadataService()

    def expand(
        self,
        inputs: Sequence[str | Path],
        recursive: bool = False,
        suffix_filter: Iterable[str] | None = None,
        cancel_event=None,
    ) -> list[ExpandedFile]:
        """展开文件和文件夹，返回去重后的 ``(path, input_root)`` 列表。

        - 单文件：``input_root=None``。
        - 文件夹：``input_root`` 为该文件夹解析后的根路径。
        - 权限错误、损坏链接等记录 warning 后跳过。
        - 不递归文件夹中的子目录，除非 ``recursive=True``。
        """

        allowed = _normalize_filter(suffix_filter)
        results: list[ExpandedFile] = []
        seen: set[str] = set()

        def add(path: Path, root: Path | None) -> None:
            key = os.path.normcase(str(path))
            if key in seen:
                return
            seen.add(key)
            results.append((path, root))

        for raw in inputs:
            if cancel_event is not None and cancel_event.is_set():
                break
            try:
                source = Path(raw).expanduser().resolve()
            except (OSError, RuntimeError) as exc:
                logger.warning("无法解析输入路径 %s: %s", raw, exc)
                continue

            if source.is_file():
                if _matches_filter(source, allowed):
                    add(source, None)
                continue

            if not source.is_dir():
                logger.warning("输入路径不存在或不是文件/文件夹: %s", source)
                continue

            root = source
            iterator: Iterable[Path]
            try:
                iterator = root.rglob("*") if recursive else root.glob("*")
                for candidate in iterator:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    try:
                        if not candidate.is_file():
                            continue
                    except OSError as exc:
                        logger.warning("检查文件失败，已跳过 %s: %s", candidate, exc)
                        continue
                    if _matches_filter(candidate, allowed):
                        add(candidate.resolve(), root)
            except OSError as exc:
                logger.warning("遍历文件夹失败 %s: %s", root, exc)

        return results

    def iter_scan(
        self,
        files: Iterable[ExpandedFile | str | Path],
        cancel_event=None,
        with_metadata: bool = False,
    ) -> Generator[ScanItem, None, None]:
        """逐个识别文件并产出 :class:`ScanItem`。

        默认不读取元数据；只有 ``with_metadata=True`` 才调用元数据服务。
        """

        for entry in files:
            if cancel_event is not None and cancel_event.is_set():
                break

            if isinstance(entry, tuple):
                path, input_root = entry
            else:
                path, input_root = Path(entry), None

            format_name, level = self.detector.detect(path)
            info = self.metadata_service.read_metadata(path) if with_metadata else {}
            error = "无法识别格式" if level is SupportLevel.ERROR else None
            if level is SupportLevel.ERROR:
                logger.warning("扫描识别失败: %s", path)
            yield ScanItem(
                path=path,
                format=format_name,
                support_level=level,
                input_root=input_root,
                info=info,
                error=error,
            )


__all__ = ["ExpandedFile", "ScanService"]
