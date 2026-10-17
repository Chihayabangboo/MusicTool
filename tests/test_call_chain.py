from __future__ import annotations

import inspect

from music_toolkit.core.models import Job
from music_toolkit.services.app_factory import bootstrap_app
from music_toolkit.services.task_service import TaskService


def test_call_chain_and_key_none(tmp_path, monkeypatch):
    app = bootstrap_app()
    src = tmp_path / "sample.wav"
    src.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 8)
    dst = tmp_path / "sample.mp3"
    sequence: list[object] = []

    original_detect = app.detector.detect
    original_get = app.registry.get
    plugin = app.registry.get("wav")
    assert plugin is not None
    original_convert = plugin.convert

    def detect_spy(path):
        sequence.append("detect")
        return original_detect(path)

    def get_spy(format_name):
        sequence.append("get")
        return original_get(format_name)

    def convert_spy(src_path, dst_path, cancel_event=None, key=None):
        sequence.append(("convert", key))
        return original_convert(src_path, dst_path, cancel_event=cancel_event, key=key)

    monkeypatch.setattr(app.detector, "detect", detect_spy)
    monkeypatch.setattr(app.registry, "get", get_spy)
    monkeypatch.setattr(plugin, "convert", convert_spy)

    from music_toolkit.core import converter

    def fake_run_ffmpeg(src_path, dst_path, cancel_event=None):
        sequence.append("ffmpeg")
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        dst_path.write_bytes(b"converted")

    monkeypatch.setattr(converter, "run_ffmpeg", fake_run_ffmpeg)

    job = Job(id="j1", src=src)
    app.task_service.run_batch([job], app.planner_factory(tmp_path, ".mp3", False, True))

    assert sequence == ["detect", "get", ("convert", None), "ffmpeg"]
    assert job.dst == dst
    assert dst.exists()


def test_task_service_source_does_not_reference_converter():
    source = inspect.getsource(TaskService)
    assert "converter" not in source
    assert "run_ffmpeg" not in source
