from __future__ import annotations

from music_toolkit.core import metadata


def test_read_missing_file_returns_empty(tmp_path):
    assert metadata.read(tmp_path / "missing.mp3") == {}


def test_read_garbage_returns_empty(tmp_path):
    path = tmp_path / "bad.mp3"
    path.write_bytes(b"not audio")
    assert metadata.read(path) == {}
