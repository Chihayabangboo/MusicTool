from __future__ import annotations

from music_toolkit.services.app_factory import bootstrap_app


def test_encrypted_format_detection_and_placeholders(tmp_path):
    app = bootstrap_app()

    ncm = tmp_path / "song.ncm"
    ncm.write_bytes(b"CTENFDAM" + b"\x00" * 8)
    assert app.detector.detect(ncm)[0] == "ncm"
    assert app.detector.detect(ncm)[1].value == "OFFLINE"

    kgg = tmp_path / "song.kgg"
    kgg.write_bytes(b"kgg1" + b"\x00" * 12)
    assert app.detector.detect(kgg) == ("kgg", app.detector.detect(kgg)[1])
    assert app.detector.detect(kgg)[1].value == "KEYED"

    mgg1 = tmp_path / "song.mgg1"
    mgg1.write_bytes(b"\x00" * 16)
    assert app.detector.detect(mgg1)[0] == "qmc3"
    assert app.detector.detect(mgg1)[1].value == "DETECT_ONLY"
