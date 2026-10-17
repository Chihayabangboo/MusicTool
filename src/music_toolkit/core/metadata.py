"""mutagen 原始封装。任何异常都返回空字典，不向调用方抛出。"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _stringify(value) -> object:
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_stringify(item) for item in value]
    return str(value)


def read(path: str | Path) -> dict:
    """读取时长、码率与标签；失败时返回 ``{}``。"""

    try:
        import mutagen

        audio = mutagen.File(str(path))
        if audio is None:
            return {}

        info = getattr(audio, "info", None)
        tags: dict[str, object] = {}
        raw_tags = getattr(audio, "tags", None)
        if raw_tags:
            for key, value in raw_tags.items():
                tags[str(key)] = _stringify(value)

        result: dict[str, object] = {}
        duration = getattr(info, "length", None)
        if duration is not None:
            result["duration"] = float(duration)
        bitrate = getattr(info, "bitrate", None)
        if bitrate is not None:
            result["bitrate"] = int(bitrate)
        if tags:
            result["tags"] = tags
        result["format"] = type(audio).__name__
        return result
    except Exception as exc:  # mutagen 对损坏文件可能抛任意异常
        logger.warning("读取元数据失败 %s: %s", path, exc)
        return {}
