"""任务调度器。

调用链固定为：
    detector.detect -> registry.get -> plugin.convert(..., key=None)

本模块不 import ``core.converter``，也不直接调用 ffmpeg。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.errors import MusicToolkitError, UnsupportedFormat
from ..core.models import Job, JobStatus, SupportLevel

if TYPE_CHECKING:
    from ..core.detector import Detector
    from ..core.registry import PluginRegistry
    from .output_planner import OutputPlanner

logger = logging.getLogger(__name__)

TaskProgressCallback = Callable[[str, int], None]
OverallProgressCallback = Callable[[int, int], None]
DoneCallback = Callable[[str, bool, str, str], None]


def make_job(job_id: str, src: str | Path, input_root: str | Path | None = None) -> Job:
    """GUI 使用的 Job 工厂，避免 GUI 直接依赖 ``core.models``。"""

    return Job(id=job_id, src=Path(src), input_root=Path(input_root) if input_root else None)


class TaskService:
    """按批调度转换任务。"""

    def __init__(self, detector: Detector, registry: PluginRegistry) -> None:
        self.detector = detector
        self.registry = registry

    def run_batch(
        self,
        jobs: Sequence[Job],
        planner: OutputPlanner,
        on_task_progress: TaskProgressCallback | None = None,
        on_overall_progress: OverallProgressCallback | None = None,
        on_done: DoneCallback | None = None,
        cancel_event=None,
    ) -> list[Job]:
        """依次处理 jobs，返回更新后的 job 列表。

        取消后立即停止，已完成文件保留；``.part`` 由插件/ffmpeg 工具清理。
        """

        total = len(jobs)
        done = 0
        if on_overall_progress is not None:
            on_overall_progress(done, total)

        for job in jobs:
            if cancel_event is not None and cancel_event.is_set():
                job.status = JobStatus.CANCELLED
                job.error = "已取消"
                self._notify_done(on_done, job, False, "")
                logger.info("收到取消信号，停止调度")
                break

            format_name, level = self.detector.detect(job.src)
            if level in (SupportLevel.DETECT_ONLY, SupportLevel.ERROR):
                message = (
                    "仅支持格式识别，不提供转换"
                    if level is SupportLevel.DETECT_ONLY
                    else "无法识别格式"
                )
                job.status = (
                    JobStatus.SKIPPED
                    if level is SupportLevel.DETECT_ONLY
                    else JobStatus.FAILED
                )
                job.error = message
                if level is SupportLevel.ERROR:
                    logger.warning("任务识别失败 %s: %s", job.src, message)
                else:
                    logger.info("跳过仅识别格式 %s: %s", job.src, message)
                self._notify_done(on_done, job, False, "")
                done += 1
                if on_overall_progress is not None:
                    on_overall_progress(done, total)
                continue

            try:
                plugin = self.registry.get(format_name)
                if plugin is None:
                    raise UnsupportedFormat(f"未注册处理格式 {format_name!r} 的插件")

                job.dst = planner.plan(job.src, job.input_root)
                try:
                    job.dst.parent.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    raise MusicToolkitError(f"无法创建输出目录: {exc}") from exc

                job.status = JobStatus.RUNNING
                job.error = None
                if on_task_progress is not None:
                    on_task_progress(job.id, 0)

                # 框架不提供密钥输入入口，key 固定为 None。
                plugin.convert(job.src, job.dst, cancel_event=cancel_event, key=None)

                if cancel_event is not None and cancel_event.is_set() and not job.dst.exists():
                    job.status = JobStatus.CANCELLED
                    job.error = "已取消"
                    self._cleanup_part(job.dst)
                    self._notify_done(on_done, job, False, "")
                    logger.info("任务已取消: %s", job.src)
                    break

                job.status = JobStatus.SUCCESS
                job.error = None
                if on_task_progress is not None:
                    on_task_progress(job.id, 100)
                self._notify_done(on_done, job, True, str(job.dst))
                logger.info("任务成功: %s -> %s", job.src, job.dst)
            except MusicToolkitError as exc:
                job.status = JobStatus.FAILED
                job.error = str(exc)
                if job.dst is not None:
                    self._cleanup_part(job.dst)
                self._notify_done(on_done, job, False, "")
                if isinstance(exc, UnsupportedFormat) and job.error:
                    logger.warning("格式不受支持 %s: %s", job.src, job.error)
                else:
                    logger.error("任务失败 %s: %s", job.src, exc)
            except OSError as exc:
                job.status = JobStatus.FAILED
                job.error = f"I/O 错误: {exc}"
                if job.dst is not None:
                    self._cleanup_part(job.dst)
                self._notify_done(on_done, job, False, "")
                logger.error("任务 I/O 失败 %s: %s", job.src, exc)

            done += 1
            if on_overall_progress is not None:
                on_overall_progress(done, total)

            if cancel_event is not None and cancel_event.is_set():
                logger.info("收到取消信号，停止调度")
                break

        return list(jobs)

    @staticmethod
    def _notify_done(callback: DoneCallback | None, job: Job, success: bool, dst: str) -> None:
        if callback is None:
            return
        callback(job.id, success, dst, job.error or "")

    @staticmethod
    def _cleanup_part(dst: Path) -> None:
        part = dst.with_suffix(dst.suffix + ".part")
        try:
            part.unlink(missing_ok=True)
        except OSError:
            logger.warning("清理 .part 失败: %s", part)
