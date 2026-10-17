"""``python -m music_toolkit`` 入口。

无参数时启动 GUI；带参数时转交 CLI，便于 ``python -m music_toolkit --help``。
"""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) > 1:
        from music_toolkit.cli import main as cli_main

        cli_main()
        return

    from music_toolkit.gui.app import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
