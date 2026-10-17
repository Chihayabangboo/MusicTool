from __future__ import annotations

import pytest

from music_toolkit.core.errors import (
    DecryptFailed,
    FfmpegNotFound,
    MissingKey,
    MusicToolkitError,
    TranscodeFailed,
    UnsupportedFormat,
)


@pytest.mark.parametrize(
    "error_type",
    [
        MusicToolkitError,
        UnsupportedFormat,
        MissingKey,
        DecryptFailed,
        TranscodeFailed,
        FfmpegNotFound,
    ],
)
def test_each_error_carries_message(error_type):
    exc = error_type("测试消息")
    assert isinstance(exc, MusicToolkitError)
    assert str(exc) == "测试消息"
    assert exc.message == "测试消息"


def test_default_message_is_empty():
    assert str(MusicToolkitError()) == ""
