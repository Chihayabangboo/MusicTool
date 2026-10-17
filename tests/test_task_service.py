from __future__ import annotations

import threading
from pathlib import Path

from music_toolkit.core.models import Job, JobStatus, SupportLevel
from music_toolkit.services.task_service import TaskService


class FakeDetector:
    def __init__(self, levels, order):
        self.levels = levels
        self.order = order

    def detect(self, path):
        self.order.append("detect")
        level = self.levels.get(Path(path).suffix, SupportLevel.OFFLINE)
        return ("fake", level)


class FakeRegistry:
    def __init__(self, plugin, order):
        self.plugin = plugin
        self.order = order

    def get(self, format_name):
        self.order.append("get")
        return self.plugin


class FakePlugin:
    def __init__(self, order, cancel=None):
        self.order = order
        self.cancel = cancel
        self.keys = []

    def convert(self, src, dst, cancel_event=None, key=None):
        self.order.append("convert")
        self.keys.append(key)
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        if self.cancel is not None:
            Path(str(dst) + ".part").write_bytes(b"partial")
            self.cancel.set()
            return
        Path(dst).write_bytes(b"converted")


class FakePlanner:
    def __init__(self, out_dir):
        self.out_dir = Path(out_dir)

    def plan(self, src, input_root=None):
        return self.out_dir / (Path(src).stem + ".mp3")


def test_progress_and_done_callbacks(tmp_path):
    order: list[str] = []
    plugin = FakePlugin(order)
    job = Job(id="j1", src=tmp_path / "a.wav")
    progress = []
    overall = []
    done = []

    TaskService(FakeDetector({}, order), FakeRegistry(plugin, order)).run_batch(
        [job],
        FakePlanner(tmp_path / "out"),
        on_task_progress=lambda job_id, pct: progress.append((job_id, pct)),
        on_overall_progress=lambda done_count, total: overall.append((done_count, total)),
        on_done=lambda *args: done.append(args),
    )

    assert job.status is JobStatus.SUCCESS
    assert job.dst == tmp_path / "out" / "a.mp3"
    assert progress == [("j1", 0), ("j1", 100)]
    assert overall == [(0, 1), (1, 1)]
    assert done == [("j1", True, str(tmp_path / "out" / "a.mp3"), "")]
    assert plugin.keys == [None]


def test_call_order_and_key_none(tmp_path):
    order: list[str] = []
    plugin = FakePlugin(order)
    job = Job(id="j1", src=tmp_path / "a.wav")
    TaskService(FakeDetector({}, order), FakeRegistry(plugin, order)).run_batch(
        [job], FakePlanner(tmp_path / "out")
    )
    assert order[:3] == ["detect", "get", "convert"]
    assert plugin.keys == [None]


def test_cancel_stops_and_cleans_part(tmp_path):
    cancel = threading.Event()
    order: list[str] = []
    plugin = FakePlugin(order, cancel=cancel)
    jobs = [
        Job(id="j1", src=tmp_path / "a.wav"),
        Job(id="j2", src=tmp_path / "b.wav"),
    ]
    done = []

    TaskService(FakeDetector({}, order), FakeRegistry(plugin, order)).run_batch(
        jobs,
        FakePlanner(tmp_path / "out"),
        on_done=lambda *args: done.append(args),
        cancel_event=cancel,
    )

    assert jobs[0].status is JobStatus.CANCELLED
    assert jobs[1].status is JobStatus.PENDING
    assert not (tmp_path / "out" / "a.mp3.part").exists()
    assert len(done) == 1


def test_detect_only_is_skipped(tmp_path):
    order: list[str] = []
    plugin = FakePlugin(order)
    job = Job(id="j1", src=tmp_path / "a.mgg1")
    done = []
    TaskService(
        FakeDetector({".mgg1": SupportLevel.DETECT_ONLY}, order),
        FakeRegistry(plugin, order),
    ).run_batch([job], FakePlanner(tmp_path / "out"), on_done=lambda *args: done.append(args))
    assert job.status is JobStatus.SKIPPED
    assert done[0][1] is False
    assert "仅支持格式识别" in done[0][3]
    assert order == ["detect"]


def test_error_level_is_failed(tmp_path):
    order: list[str] = []
    plugin = FakePlugin(order)
    job = Job(id="j1", src=tmp_path / "a.bin")
    TaskService(
        FakeDetector({".bin": SupportLevel.ERROR}, order),
        FakeRegistry(plugin, order),
    ).run_batch([job], FakePlanner(tmp_path / "out"))
    assert job.status is JobStatus.FAILED
    assert order == ["detect"]
