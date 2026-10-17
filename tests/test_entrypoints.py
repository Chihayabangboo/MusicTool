from __future__ import annotations

from pathlib import Path


def test_main_module_locates_gui_main():
    root = Path(__file__).resolve().parents[1]
    content = (root / "src" / "music_toolkit" / "__main__.py").read_text(encoding="utf-8")
    assert "gui.app" in content
    assert "gui_main" in content
    assert "main()" in content


def test_entrypoint_importable():
    from music_toolkit.cli import main as cli_main
    from music_toolkit.gui.app import main as gui_main

    assert callable(cli_main)
    assert callable(gui_main)
