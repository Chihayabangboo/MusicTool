from __future__ import annotations

from music_toolkit.core import converter
from music_toolkit.core.errors import FfmpegNotFound, TranscodeFailed


class FakePopen:
    def __init__(self, command, returncode=0, write_part=True, **kwargs):
        self.command = command
        self.returncode = returncode
        self.calls = 0
        self.terminated = False
        if write_part:
            target = __import__("pathlib").Path(command[-1])
            target.write_bytes(b"fake-audio")
        if returncode != 0:
            stderr = kwargs.get("stderr")
            if stderr:
                stderr.write("simulated ffmpeg failure")
                stderr.flush()

    def poll(self):
        self.calls += 1
        if self.calls >= 2:
            return self.returncode
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.terminated = True


def test_missing_ffmpeg_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "find_ffmpeg", lambda: None)
    try:
        converter.run_ffmpeg(tmp_path / "a.wav", tmp_path / "b.mp3")
    except FfmpegNotFound as exc:
        assert "ffmpeg" in str(exc)
    else:
        raise AssertionError("应当抛出 FfmpegNotFound")


def test_success_replaces_part(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(converter.subprocess, "Popen", FakePopen)
    dst = tmp_path / "b.mp3"
    converter.run_ffmpeg(tmp_path / "a.wav", dst)
    assert dst.read_bytes() == b"fake-audio"
    assert not (tmp_path / "b.mp3.part").exists()


def test_failure_removes_part_and_reports_stderr(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        converter.subprocess,
        "Popen",
        lambda *a, **kw: FakePopen(*a, returncode=1, **kw),
    )
    try:
        converter.run_ffmpeg(tmp_path / "a.wav", tmp_path / "b.mp3")
    except TranscodeFailed as exc:
        assert "simulated ffmpeg failure" in str(exc)
    else:
        raise AssertionError("应当抛出 TranscodeFailed")
    assert not (tmp_path / "b.mp3.part").exists()
    assert not (tmp_path / "b.mp3").exists()


def test_pre_cancel_returns_without_output(tmp_path, monkeypatch):
    import threading

    monkeypatch.setattr(converter, "find_ffmpeg", lambda: "ffmpeg")
    event = threading.Event()
    event.set()
    converter.run_ffmpeg(tmp_path / "a.wav", tmp_path / "b.mp3", cancel_event=event)
    assert not (tmp_path / "b.mp3").exists()
    assert not (tmp_path / "b.mp3.part").exists()
