"""服务层：业务编排，不依赖任何 GUI 库。"""

from __future__ import annotations

__all__ = [
    "AppContext",
    "bootstrap_app",
]


def __getattr__(name: str):
    # 延迟导入，避免仅导入 services 包时加载过多子模块。
    if name in {"AppContext", "bootstrap_app"}:
        from .app_factory import AppContext, bootstrap_app

        return {"AppContext": AppContext, "bootstrap_app": bootstrap_app}[name]
    raise AttributeError(name)
