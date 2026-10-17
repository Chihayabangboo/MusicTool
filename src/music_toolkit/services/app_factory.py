"""统一初始化工厂。GUI 和 CLI 都只通过 ``bootstrap_app()`` 获取依赖。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..core.detector import Detector
from ..core.registry import PluginRegistry
from .metadata_service import MetadataService
from .output_planner import OutputPlanner, make_planner
from .plugin_loader import load_builtin_plugins
from .scan_service import ScanService
from .task_service import TaskService

PlannerFactory = Callable[[Path, str, bool, bool], OutputPlanner]


@dataclass
class AppContext:
    """应用依赖容器。"""

    registry: PluginRegistry
    detector: Detector
    metadata_service: MetadataService
    scan_service: ScanService
    task_service: TaskService
    planner_factory: PlannerFactory


def bootstrap_app() -> AppContext:
    """创建一套全新的、已注册内置插件的依赖。

    每次都创建独立 registry，连续调用互不影响。
    """

    registry = PluginRegistry()
    load_builtin_plugins(registry)
    detector = Detector()
    metadata_service = MetadataService()
    scan_service = ScanService(detector, metadata_service)
    task_service = TaskService(detector, registry)
    return AppContext(
        registry=registry,
        detector=detector,
        metadata_service=metadata_service,
        scan_service=scan_service,
        task_service=task_service,
        planner_factory=make_planner,
    )


__all__ = ["AppContext", "PlannerFactory", "bootstrap_app"]
