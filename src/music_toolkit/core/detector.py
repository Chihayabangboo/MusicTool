"""格式识别器。

约束：只读取文件前 16 字节，不读取数据体，不执行任何转换或解密。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .models import SupportLevel

logger = logging.getLogger(__name__)

HEAD_SIZE = 16

#: 扩展名 -> 归并后的 format_name。仅用于魔数未命中时兜底。
EXTENSION_MAP: dict[str, str] = {
    ".wav": "wav",
    ".flac": "flac",
    ".mp3": "mp3",
    ".ogg": "ogg",
    ".ncm": "ncm",
    ".qmc0": "qmc1",
    ".qmc3": "qmc1",
    ".qmc2": "qmc1",
    ".qmcogg": "qmc1",
    ".qmcflac": "qmc1",
    ".tkm": "qmc1",
    ".mflac": "qmc2",
    ".mgg": "qmc2",
    ".mgg1": "qmc3",
    ".mgg2": "qmc3",
    ".mmp4": "qmc3",
    ".kgm": "kgm",
    ".kgma": "kgm",
    ".vpr": "vpr",
    ".kgg": "kgg",
    ".kwm": "kwm",
}

#: format_name -> 支持级别（唯一版本）。
SUPPORT_LEVELS: dict[str, SupportLevel] = {
    "wav": SupportLevel.OFFLINE,
    "flac": SupportLevel.OFFLINE,
    "mp3": SupportLevel.OFFLINE,
    "ogg": SupportLevel.OFFLINE,
    "ncm": SupportLevel.OFFLINE,
    "qmc1": SupportLevel.OFFLINE,
    "qmc2": SupportLevel.OFFLINE,
    "kgm": SupportLevel.OFFLINE,
    "kgma": SupportLevel.OFFLINE,
    "vpr": SupportLevel.OFFLINE,
    "kwm": SupportLevel.OFFLINE,
    "kgg": SupportLevel.KEYED,
    "qmc3": SupportLevel.DETECT_ONLY,
    "UNKNOWN": SupportLevel.ERROR,
}


@dataclass(frozen=True)
class MagicSignature:
    """一个公开文件头签名。

    ``patterns`` 中任意一个在 ``offset`` 处完全匹配即视为命中；
    如果提供了 ``secondary_offset/secondary_patterns``，两段必须同时命中。
    """

    format_name: str
    offset: int
    patterns: tuple[bytes, ...]
    description: str
    secondary_offset: int | None = None
    secondary_patterns: tuple[bytes, ...] = ()

    def matches(self, head: bytes) -> bool:
        if not self._match_at(head, self.offset, self.patterns):
            return False
        if self.secondary_offset is None:
            return True
        return self._match_at(head, self.secondary_offset, self.secondary_patterns)

    @staticmethod
    def _match_at(head: bytes, offset: int, patterns: tuple[bytes, ...]) -> bool:
        for pattern in patterns:
            end = offset + len(pattern)
            if len(head) >= end and head[offset:end] == pattern:
                return True
        return False


#: 魔数表。顺序即匹配优先级，命中即停。
#: 这些都是公开文件头，不包含任何加密数据体信息。
MAGIC_TABLE: tuple[MagicSignature, ...] = (
    MagicSignature(
        format_name="wav",
        offset=0,
        patterns=(b"RIFF",),
        secondary_offset=8,
        secondary_patterns=(b"WAVE",),
        description="RIFF....WAVE",
    ),
    MagicSignature(
        format_name="flac",
        offset=0,
        patterns=(b"fLaC",),
        description="fLaC",
    ),
    MagicSignature(
        format_name="ogg",
        offset=0,
        patterns=(b"OggS",),
        description="OggS",
    ),
    MagicSignature(
        format_name="mp3",
        offset=0,
        patterns=(b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"),
        description="ID3 或 MPEG 帧同步字",
    ),
    MagicSignature(
        format_name="ncm",
        offset=0,
        patterns=(b"CTENFDAM",),
        description="CTENFDAM",
    ),
    MagicSignature(
        format_name="kwm",
        offset=0,
        patterns=(b"yeelion",),
        description="yeelion",
    ),
    MagicSignature(
        format_name="kgm",
        offset=0,
        patterns=(b"kgm1", b"kgm2"),
        description="kgm1 / kgm2（kgma 归并到 kgm）",
    ),
    MagicSignature(
        format_name="kgg",
        offset=0,
        patterns=(b"kgg1",),
        description="kgg1",
    ),
    MagicSignature(
        format_name="qmc2",
        offset=0,
        patterns=(b"QTag", b"STag"),
        description="QTag / STag（mflac / mgg 归并为 qmc2）",
    ),
)


def normalize_extension(suffix: str) -> str:
    """把扩展名归一化为 :data:`EXTENSION_MAP` 中的 format_name。

    接受 ``.wav``、``wav``、``.WAV`` 等形式；未知扩展名返回 ``"UNKNOWN"``。
    """

    value = (suffix or "").strip().lower()
    if not value:
        return "UNKNOWN"
    if not value.startswith("."):
        value = "." + value
    return EXTENSION_MAP.get(value, "UNKNOWN")


def support_level_for(format_name: str) -> SupportLevel:
    """返回格式名对应的支持级别；未知格式返回 ``ERROR``。"""

    return SUPPORT_LEVELS.get(format_name, SupportLevel.ERROR)


class Detector:
    """只做识别：读取前 16 字节 + 扩展名，返回 ``(format_name, level)``。"""

    def __init__(self, magic_table: tuple[MagicSignature, ...] | None = None) -> None:
        self.magic_table = MAGIC_TABLE if magic_table is None else magic_table

    def detect(self, path: str | Path) -> tuple[str, SupportLevel]:
        """识别文件格式。任何 I/O 异常都退化为 ``("UNKNOWN", ERROR)``。"""

        file_path = Path(path)
        try:
            with file_path.open("rb") as handle:
                head = handle.read(HEAD_SIZE)
        except (OSError, ValueError) as exc:
            logger.warning("无法读取文件头 %s: %s", file_path, exc)
            return ("UNKNOWN", SupportLevel.ERROR)

        if not head:
            logger.warning("文件为空或不可读: %s", file_path)
            return ("UNKNOWN", SupportLevel.ERROR)

        magic_format = self._match_magic(head)
        if magic_format is not None:
            return (magic_format, support_level_for(magic_format))

        # 截断文件不退回扩展名。
        if len(head) < HEAD_SIZE:
            logger.warning("文件头不足 %d 字节且未命中魔数: %s", HEAD_SIZE, file_path)
            return ("UNKNOWN", SupportLevel.ERROR)

        by_extension = normalize_extension(file_path.suffix)
        if by_extension != "UNKNOWN":
            return (by_extension, support_level_for(by_extension))

        logger.warning("无法识别文件格式: %s", file_path)
        return ("UNKNOWN", SupportLevel.ERROR)

    def _match_magic(self, head: bytes) -> str | None:
        for signature in self.magic_table:
            if signature.matches(head):
                return signature.format_name
        return None
