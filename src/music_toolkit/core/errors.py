"""框架统一异常。所有业务异常都必须继承 :class:`MusicToolkitError`。"""

from __future__ import annotations


class MusicToolkitError(Exception):
    """框架基础异常。"""

    def __init__(self, message: str = "") -> None:
        self.message = message
        super().__init__(message)


class UnsupportedFormat(MusicToolkitError):
    """格式不受支持，或当前框架不提供该格式的处理能力。"""


class MissingKey(MusicToolkitError):
    """该格式在接口层面需要密钥，但框架不提供密钥输入入口。"""


class DecryptFailed(MusicToolkitError):
    """预留的解密失败异常；当前框架不会执行解密。"""


class TranscodeFailed(MusicToolkitError):
    """ffmpeg 转码失败。"""


class FfmpegNotFound(MusicToolkitError):
    """系统 PATH 中找不到 ffmpeg。"""
