from __future__ import annotations

from pathlib import Path

import pytest

from music_toolkit.core import converter
from music_toolkit.services.app_factory import bootstrap_app

FIXTURES = Path(__file__).parent / "fixtures"
NAMES = ["silence.wav", "silence.flac", "silence.mp3", "silence.ogg"]


@pytest.mark.skipif(
    not converter.is_ffmpeg_available(),
    reason="未检测到 ffmpeg，跳过真实端到端转码",
)
@pytest.mark.parametrize("name", NAMES)
def test_real_transcode(tmp_path, name):
    source = FIXTURES / name
    if not source.is_file():
        pytest.skip(f"缺少 ffmpeg 生成的测试样本 {name}")
    app = bootstrap_app()
    format_name, level = app.detector.detect(source)
    assert level.value == "OFFLINE", (format_name, level)

    target = tmp_path / (source.stem + ".mp3")
    job = __import__("music_toolkit.core.models", fromlist=["Job"]).Job(
        id="e2e", src=source
    )
    done = []
    app.task_service.run_batch(
        [job],
        app.planner_factory(tmp_path, ".mp3", False, True),
        on_done=lambda *args: done.append(args),
    )
    assert job.status.value == "SUCCESS", done
    assert target.exists() and target.stat().st_size > 0


@pytest.mark.skipif(
    not converter.is_ffmpeg_available(),
    reason="未检测到 ffmpeg，跳过真实转码的 CLI 用例",
)
def test_cli_convert_real(tmp_path):
    from typer.testing import CliRunner

    from music_toolkit.cli import app

    result = CliRunner().invoke(
        app,
        ["convert", str(FIXTURES / "silence.wav"), str(tmp_path / "out.ogg")],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out.ogg").stat().st_size > 0
