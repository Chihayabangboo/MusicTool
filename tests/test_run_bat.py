from __future__ import annotations

from pathlib import Path


def test_run_bat_exists_and_has_required_logic():
    root = Path(__file__).resolve().parents[1]
    path = root / "run.bat"
    assert path.is_file()
    content = path.read_text(encoding="utf-8").lower()
    assert "chcp 65001" in content
    assert "%~dp0" in content
    assert "where python" in content
    assert "import music_toolkit" in content
    assert "pip install -e ." in content
    assert "import ttkbootstrap, tkinterdnd2, mutagen" in content
    assert "python -m music_toolkit" in content
    assert "pause" in content
    assert "errorlevel" in content
    assert "ffmpeg" in content


def test_run_bat_has_no_network_or_decrypt_logic():
    root = Path(__file__).resolve().parents[1]
    content = (root / "run.bat").read_text(encoding="utf-8").lower()
    for forbidden in ("curl", "wget", "invoke-webrequest", "start-bitstransfer"):
        assert forbidden not in content
