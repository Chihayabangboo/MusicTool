from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from music_toolkit.cli import app
from music_toolkit.core.errors import FfmpegNotFound


def _valid_wav(tmp_path: Path) -> Path:
    path = tmp_path / "sample.wav"
    path.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 20)
    return path


def test_help():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "detect" in result.output
    assert "convert" in result.output


def test_detect_and_info(tmp_path):
    source = _valid_wav(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["detect", str(source)])
    assert result.exit_code == 0
    assert "wav" in result.output
    assert "OFFLINE" in result.output

    result = runner.invoke(app, ["info", str(source)])
    assert result.exit_code == 0
    assert "wav" in result.output


def test_convert_with_mocked_ffmpeg(tmp_path, monkeypatch):
    from music_toolkit.core import converter

    source = _valid_wav(tmp_path)
    target = tmp_path / "out.mp3"

    def fake_run(src, dst, cancel_event=None):
        Path(dst).write_bytes(b"converted")

    monkeypatch.setattr(converter, "run_ffmpeg", fake_run)
    result = CliRunner().invoke(app, ["convert", str(source), str(target)])
    assert result.exit_code == 0, result.output
    assert target.exists()


def test_convert_reports_missing_ffmpeg(tmp_path, monkeypatch):
    from music_toolkit.core import converter

    source = _valid_wav(tmp_path)
    target = tmp_path / "out.mp3"

    def fail(src, dst, cancel_event=None):
        raise FfmpegNotFound("未检测到 ffmpeg，转码功能不可用")

    monkeypatch.setattr(converter, "run_ffmpeg", fail)
    result = CliRunner().invoke(app, ["convert", str(source), str(target)])
    assert result.exit_code == 1
    assert "未检测到 ffmpeg" in result.output


def test_scan(tmp_path):
    _valid_wav(tmp_path)
    result = CliRunner().invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "wav" in result.output
    assert "共扫描 1 个文件" in result.output
