"""输出路径规划。"""

from __future__ import annotations

import re
from pathlib import Path

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f\x7f]')


def sanitize_stem(stem: str) -> str:
    """只清洗文件名部分的非法字符；路径分隔符不清洗。"""

    return _ILLEGAL_FILENAME_CHARS.sub("_", stem)


class OutputPlanner:
    """计算输出文件名与目录，不创建目录。"""

    def __init__(
        self,
        out_dir: str | Path,
        target_ext: str,
        keep_structure: bool = False,
        overwrite: bool = False,
    ) -> None:
        self.out_dir = Path(out_dir)
        ext = (target_ext or ".mp3").strip().lower()
        if not ext.startswith("."):
            ext = "." + ext
        self.target_ext = ext
        self.keep_structure = keep_structure
        self.overwrite = overwrite

    def plan(self, src: str | Path, input_root: str | Path | None = None) -> Path:
        """返回目标路径；不创建任何目录。"""

        source = Path(src)
        root: Path | None = Path(input_root) if input_root is not None else None
        directory = self.out_dir
        if self.keep_structure and root is not None:
            try:
                relative_parent = source.parent.relative_to(root)
            except ValueError:
                relative_parent = Path()
            directory = self.out_dir / relative_parent

        filename = sanitize_stem(source.stem) + self.target_ext
        candidate = directory / filename
        if self.overwrite or not candidate.exists():
            return candidate

        counter = 1
        while True:
            numbered = directory / f"{sanitize_stem(source.stem)}_{counter}{self.target_ext}"
            if not numbered.exists():
                return numbered
            counter += 1


def make_planner(
    out_dir: str | Path,
    target_ext: str,
    keep_structure: bool,
    overwrite: bool,
) -> OutputPlanner:
    """工厂函数，供 :class:`~music_toolkit.services.app_factory.AppContext` 使用。"""

    return OutputPlanner(out_dir, target_ext, keep_structure, overwrite)


__all__ = ["OutputPlanner", "make_planner", "sanitize_stem"]
