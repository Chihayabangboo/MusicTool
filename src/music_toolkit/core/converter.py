"""ffmpeg 子进程工具函数。

本模块只负责调用 ffmpeg，不注册插件，也不被 TaskService 直接调用。
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .errors import FfmpegNotFound, TranscodeFailed

logger = logging.getLogger(__name__)

_FFMPEG = "ffmpeg"
_CANCEL_POLL_SECONDS = 0.1
_TERMINATE_TIMEOUT_SECONDS = 3.0
_STDERR_SUMMARY_LIMIT = 1200

#: 输出扩展名 -> ffmpeg 编码参数。
_CODEC_ARGS: dict[str, list[str]] = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".flac": ["-c:a", "flac"],
    ".wav": ["-c:a", "pcm_s16le"],
    ".ogg": ["-c:a", "libvorbis", "-q:a", "5"],
}

#: 输出扩展名 -> ffmpeg muxer。`.part` 临时后缀无法让 ffmpeg 推断容器，必须显式指定。
_FORMAT_ARGS: dict[str, list[str]] = {
    ".mp3": ["-f", "mp3"],
    ".flac": ["-f", "flac"],
    ".wav": ["-f", "wav"],
    ".ogg": ["-f", "ogg"],
}


def find_ffmpeg() -> str | None:
    """返回 ffmpeg 可执行文件路径；找不到时返回 ``None``。

    优先使用系统 PATH 中的 ffmpeg。若用户额外安装了 ``imageio-ffmpeg``，
    则在系统缺失时使用它自带的 ffmpeg 可执行文件作为可选降级；本框架
    不下载任何文件。两条路径都是普通 ffmpeg 子进程调用。
    """

    executable = shutil.which(_FFMPEG)
    if executable:
        return executable
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found]

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).is_file():
            return bundled
    except Exception:  # 可选依赖，任何异常都退回“不可用”
        return None
    return None


def is_ffmpeg_available() -> bool:
    """检测是否有可用的 ffmpeg（系统 PATH 或可选的 imageio-ffmpeg）。"""

    return find_ffmpeg() is not None


def _part_path(dst: Path) -> Path:
    return dst.with_suffix(dst.suffix + ".part")


def _cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("清理临时文件失败: %s", path)


def _terminate(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=_TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=_TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            logger.warning("ffmpeg 子进程无法终止")
    except OSError:
        logger.warning("终止 ffmpeg 子进程失败")


def run_ffmpeg(
    src: str | Path,
    dst: str | Path,
    cancel_event=None,
) -> None:
    """把 ``src`` 转码为 ``dst``。

    先写 ``<dst>.part``，成功后用 :func:`os.replace` 原子替换。
    取消或失败时删除 ``.part``。取消时直接返回，由调度器根据
    ``cancel_event`` 标记任务状态。
    """

    source = Path(src)
    target = Path(dst)
    executable = find_ffmpeg()
    if not executable:
        raise FfmpegNotFound("未检测到 ffmpeg，无法执行转码；请先安装 ffmpeg 并加入 PATH")

    if cancel_event is not None and cancel_event.is_set():
        return

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise TranscodeFailed(f"无法创建输出目录 {target.parent}: {exc}") from exc

    part = _part_path(target)
    _cleanup(part)

    suffix = target.suffix.lower()
    codec_args = _CODEC_ARGS.get(suffix, [])
    format_args = _FORMAT_ARGS.get(suffix, [])
    command = [
        executable,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        *codec_args,
        *format_args,
        str(part),
    ]

    log_file = tempfile.NamedTemporaryFile(
        mode="w+",
        prefix=".music-toolkit-ffmpeg-",
        suffix=".log",
        dir=target.parent,
        delete=False,
        encoding="utf-8",
        errors="replace",
    )
    log_path = Path(log_file.name)
    stderr_text = ""
    process: subprocess.Popen | None = None
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
        )
        while True:
            returncode = process.poll()
            if returncode is not None:
                break
            if cancel_event is not None and cancel_event.is_set():
                logger.info("转码被取消: %s", source)
                _terminate(process)
                _cleanup(part)
                return
            time.sleep(_CANCEL_POLL_SECONDS)

        log_file.flush()
        try:
            stderr_text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            stderr_text = ""

        if process.returncode != 0:
            summary = stderr_text.strip()[-_STDERR_SUMMARY_LIMIT:] or "ffmpeg 返回非零退出码"
            raise TranscodeFailed(f"ffmpeg 转码失败: {summary}")

        if cancel_event is not None and cancel_event.is_set():
            _cleanup(part)
            return

        if not part.exists():
            raise TranscodeFailed("ffmpeg 未生成输出文件")
        os.replace(part, target)
        logger.info("转码完成: %s -> %s", source, target)
    except FfmpegNotFound:
        _cleanup(part)
        raise
    except TranscodeFailed:
        _cleanup(part)
        raise
    except OSError as exc:
        _cleanup(part)
        if isinstance(exc, FileNotFoundError):
            raise FfmpegNotFound("未检测到 ffmpeg，无法执行转码") from exc
        raise TranscodeFailed(f"ffmpeg 调用失败: {exc}") from exc
    finally:
        try:
            log_file.close()
        except OSError:
            pass
        _cleanup(log_path)
        _cleanup(part)
