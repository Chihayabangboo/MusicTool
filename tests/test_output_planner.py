from __future__ import annotations

from music_toolkit.core.detector import Detector
from music_toolkit.services.output_planner import OutputPlanner, sanitize_stem
from music_toolkit.services.scan_service import ScanService


def test_duplicate_gets_number_before_extension(tmp_path):
    (tmp_path / "song.mp3").write_bytes(b"x")
    planner = OutputPlanner(tmp_path, "mp3")
    assert planner.plan(tmp_path / "song.wav") == tmp_path / "song_1.mp3"

    (tmp_path / "song_1.mp3").write_bytes(b"x")
    assert planner.plan(tmp_path / "song.wav") == tmp_path / "song_2.mp3"


def test_overwrite_returns_exact_path(tmp_path):
    (tmp_path / "song.mp3").write_bytes(b"x")
    planner = OutputPlanner(tmp_path, ".mp3", overwrite=True)
    assert planner.plan(tmp_path / "song.wav") == tmp_path / "song.mp3"


def test_keep_structure_restores_relative_directory(tmp_path):
    root = tmp_path / "album"
    source = root / "cd1" / "song.wav"
    out = tmp_path / "out"
    planner = OutputPlanner(out, "flac", keep_structure=True)
    assert planner.plan(source, root) == out / "cd1" / "song.flac"


def test_no_structure_flattens(tmp_path):
    root = tmp_path / "album"
    source = root / "cd1" / "song.wav"
    planner = OutputPlanner(tmp_path / "out", "mp3", keep_structure=False)
    assert planner.plan(source, root) == tmp_path / "out" / "song.mp3"


def test_sanitize_replaces_illegal_chars_but_not_separators():
    assert sanitize_stem('a<b>c:d"e|f?g*h') == "a_b_c_d_e_f_g_h"
    assert sanitize_stem("a/b\\c") == "a/b\\c"
    assert sanitize_stem("ok\x00name\x1f") == "ok_name_"


def test_mixed_inputs_have_correct_input_root(tmp_path):
    root = tmp_path / "folder"
    nested = root / "sub"
    nested.mkdir(parents=True)
    (nested / "a.wav").write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    single_dir = tmp_path / "single"
    single_dir.mkdir()
    (single_dir / "b.mp3").write_bytes(b"ID3\x00")

    service = ScanService(Detector())
    entries = service.expand([single_dir / "b.mp3", root], recursive=True)
    by_name = {path.name: input_root for path, input_root in entries}
    assert by_name["b.mp3"] is None
    assert by_name["a.wav"] == root.resolve()


def test_planner_does_not_create_directories(tmp_path):
    target = tmp_path / "missing" / "song.mp3"
    planner = OutputPlanner(target.parent, "mp3")
    result = planner.plan(tmp_path / "song.wav")
    assert result == target
    assert not target.parent.exists()
