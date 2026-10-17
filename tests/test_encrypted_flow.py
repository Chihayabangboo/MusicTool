from __future__ import annotations

from music_toolkit.core.models import Job
from music_toolkit.services.app_factory import bootstrap_app


def _run(tmp_path, name: str, content: bytes):
    app = bootstrap_app()
    source = tmp_path / name
    source.write_bytes(content)
    job = Job(id="j1", src=source)
    results = []
    app.task_service.run_batch(
        [job],
        app.planner_factory(tmp_path / "out", ".mp3", False, True),
        on_done=lambda *args: results.append(args),
    )
    return job, results


def test_ncm_is_offline_but_convert_is_unsupported(tmp_path):
    job, results = _run(tmp_path, "song.ncm", b"CTENFDAM" + b"\x00" * 8)
    assert job.status.value == "FAILED"
    assert "不提供该格式的解密能力" in (job.error or "")
    assert results and results[0][1] is False


def test_kgg_is_keyed_and_missing_key(tmp_path):
    job, _ = _run(tmp_path, "song.kgg", b"kgg1" + b"\x00" * 12)
    assert job.status.value == "FAILED"
    assert "需要密钥" in (job.error or "")


def test_mgg1_is_detect_only_and_skipped(tmp_path):
    job, _ = _run(tmp_path, "song.mgg1", b"\x00" * 16)
    assert job.status.value == "SKIPPED"
    assert "仅支持格式识别" in (job.error or "")
