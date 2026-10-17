from __future__ import annotations

import struct

from music_toolkit.core.detector import (
    EXTENSION_MAP,
    MAGIC_TABLE,
    SUPPORT_LEVELS,
    Detector,
    normalize_extension,
)
from music_toolkit.core.models import SupportLevel


def _write(path, data: bytes) -> None:
    path.write_bytes(data)


def _wav_head() -> bytes:
    return b"RIFF" + struct.pack("<I", 36) + b"WAVEfmt "


def test_offline_audio_formats(tmp_path):
    detector = Detector()
    samples = {
        "a.wav": _wav_head() + b"\x00" * 8,
        "b.flac": b"fLaC" + b"\x00" * 12,
        "c.ogg": b"OggS" + b"\x00" * 12,
        "d.mp3": b"ID3" + b"\x00" * 13,
    }
    for name, content in samples.items():
        path = tmp_path / name
        _write(path, content)
        format_name, level = detector.detect(path)
        assert format_name == name.split(".")[1]
        assert level is SupportLevel.OFFLINE


def test_magic_takes_priority_over_extension(tmp_path):
    path = tmp_path / "renamed.ncm"
    _write(path, _wav_head() + b"\x00" * 8)
    assert Detector().detect(path) == ("wav", SupportLevel.OFFLINE)


def test_empty_file_is_error(tmp_path):
    path = tmp_path / "empty.wav"
    _write(path, b"")
    assert Detector().detect(path) == ("UNKNOWN", SupportLevel.ERROR)


def test_truncated_magic_is_recognized(tmp_path):
    path = tmp_path / "short.ncm"
    _write(path, b"CTENFDAM")  # 8 字节，足以命中 ncm
    assert Detector().detect(path) == ("ncm", SupportLevel.OFFLINE)


def test_truncated_unknown_does_not_fall_back_to_extension(tmp_path):
    path = tmp_path / "short.wav"
    _write(path, b"XXXXYYYY")
    assert Detector().detect(path) == ("UNKNOWN", SupportLevel.ERROR)


def test_missing_file_is_error(tmp_path):
    assert Detector().detect(tmp_path / "missing.mp3") == ("UNKNOWN", SupportLevel.ERROR)


def test_normalize_extension_table():
    for suffix, expected in EXTENSION_MAP.items():
        assert normalize_extension(suffix) == expected
        assert normalize_extension(suffix.upper()) == expected
        assert normalize_extension(suffix.lstrip(".")) == expected
    assert normalize_extension(".flac") == "flac"
    assert normalize_extension("mp3") == "mp3"
    assert normalize_extension(".aac") == "UNKNOWN"
    assert normalize_extension("") == "UNKNOWN"


def test_extension_fallback_when_magic_missing(tmp_path):
    path = tmp_path / "fallback.flac"
    _write(path, b"\x00" * 16)
    assert Detector().detect(path) == ("flac", SupportLevel.OFFLINE)


def test_qmc2_magic_and_qmc3_extension(tmp_path):
    qtag = tmp_path / "a.mflac"
    _write(qtag, b"QTag" + b"\x00" * 12)
    assert Detector().detect(qtag) == ("qmc2", SupportLevel.OFFLINE)

    mgg1 = tmp_path / "b.mgg1"
    _write(mgg1, b"\x00" * 16)
    assert Detector().detect(mgg1) == ("qmc3", SupportLevel.DETECT_ONLY)


def test_support_levels_table():
    expected = {
        "wav": SupportLevel.OFFLINE,
        "flac": SupportLevel.OFFLINE,
        "mp3": SupportLevel.OFFLINE,
        "ogg": SupportLevel.OFFLINE,
        "ncm": SupportLevel.OFFLINE,
        "qmc1": SupportLevel.OFFLINE,
        "qmc2": SupportLevel.OFFLINE,
        "kgm": SupportLevel.OFFLINE,
        "kgma": SupportLevel.OFFLINE,
        "vpr": SupportLevel.OFFLINE,
        "kwm": SupportLevel.OFFLINE,
        "kgg": SupportLevel.KEYED,
        "qmc3": SupportLevel.DETECT_ONLY,
        "UNKNOWN": SupportLevel.ERROR,
    }
    assert expected == SUPPORT_LEVELS


def test_magic_table_contents():
    names = {signature.format_name for signature in MAGIC_TABLE}
    assert {"wav", "flac", "ogg", "mp3", "ncm"}.issubset(names)
    assert len(MAGIC_TABLE) == len(set(MAGIC_TABLE))
