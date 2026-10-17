"""命令行界面。所有命令通过 ``bootstrap_app()`` 获取依赖。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer

from .core.errors import MusicToolkitError
from .services.app_factory import bootstrap_app

app = typer.Typer(
    help="本地音乐文件格式识别与转码工具（学习用途）。",
    no_args_is_help=True,
    add_completion=False,
)


def _setup_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s %(name)s: %(message)s",
        )


def _print_error(message: str) -> None:
    typer.secho(f"错误: {message}", fg=typer.colors.RED, err=True)


@app.command()
def detect(path: Path = typer.Argument(..., exists=False, help="要识别的文件")) -> None:
    """识别文件格式与支持级别。"""

    _setup_logging()
    try:
        ctx = bootstrap_app()
        format_name, level = ctx.detector.detect(path)
        typer.echo(f"格式: {format_name}")
        typer.echo(f"支持级别: {level.value}")
        if level.value == "ERROR":
            raise typer.Exit(code=1)
    except MusicToolkitError as exc:
        _print_error(str(exc))
        raise typer.Exit(code=1) from exc


@app.command()
def info(path: Path = typer.Argument(..., exists=False, help="要读取信息的文件")) -> None:
    """识别格式并输出元数据。"""

    _setup_logging()
    try:
        ctx = bootstrap_app()
        format_name, level = ctx.detector.detect(path)
        metadata = ctx.metadata_service.read_metadata(path)
        typer.echo(f"文件: {path}")
        typer.echo(f"格式: {format_name}")
        typer.echo(f"支持级别: {level.value}")
        typer.echo("元数据:")
        typer.echo(json.dumps(metadata, ensure_ascii=False, indent=2, default=str))
    except MusicToolkitError as exc:
        _print_error(str(exc))
        raise typer.Exit(code=1) from exc


class _ExactPlanner:
    """CLI convert 使用：目标路径就是用户给出的 dst。"""

    def __init__(self, dst: Path) -> None:
        self.dst = dst

    def plan(self, src: Path, input_root: Path | None = None) -> Path:
        return self.dst


@app.command()
def convert(
    src: Path = typer.Argument(..., exists=False, help="源文件"),
    dst: Path = typer.Argument(..., help="目标文件"),
) -> None:
    """把单个文件转换为目标格式（走 TaskService.run_batch）。"""

    _setup_logging()
    if not src.is_file():
        _print_error(f"源文件不存在: {src}")
        raise typer.Exit(code=1)
    if dst.suffix.lower() not in {".mp3", ".flac", ".wav", ".ogg"}:
        _print_error("目标扩展名必须是 .mp3 / .flac / .wav / .ogg")
        raise typer.Exit(code=1)

    from .core.models import Job

    ctx = bootstrap_app()
    job = Job(id="cli-1", src=src, input_root=None)
    outcome: dict[str, object] = {"success": False, "error": ""}

    def on_done(job_id: str, success: bool, dst_or_empty: str, error: str) -> None:
        outcome["success"] = success
        outcome["error"] = error

    try:
        ctx.task_service.run_batch(
            [job],
            _ExactPlanner(dst),
            on_done=on_done,
        )
    except MusicToolkitError as exc:
        _print_error(str(exc))
        raise typer.Exit(code=1) from exc

    if not outcome["success"]:
        _print_error(str(outcome["error"] or "转换失败"))
        raise typer.Exit(code=1)
    typer.echo(f"转换完成: {dst}")


@app.command()
def scan(
    directory: Path = typer.Argument(..., exists=False, help="要扫描的文件夹"),
    recursive: bool = typer.Option(False, "--recursive", help="包含子文件夹"),
    with_metadata: bool = typer.Option(False, "--with-metadata", help="读取元数据"),
) -> None:
    """扫描文件夹，输出识别结果。"""

    _setup_logging()
    if not directory.is_dir():
        _print_error(f"文件夹不存在: {directory}")
        raise typer.Exit(code=1)

    try:
        ctx = bootstrap_app()
        entries = ctx.scan_service.expand([directory], recursive=recursive)
        count = 0
        for item in ctx.scan_service.iter_scan(entries, with_metadata=with_metadata):
            count += 1
            typer.echo(f"{item.format}\t{item.support_level.value}\t{item.path}")
        typer.echo(f"共扫描 {count} 个文件")
    except MusicToolkitError as exc:
        _print_error(str(exc))
        raise typer.Exit(code=1) from exc


def main() -> None:
    """console_scripts / python -m 的 CLI 入口。"""

    app()


if __name__ == "__main__":
    main()
