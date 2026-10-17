"""插件注册表。不主动发现插件，也不 import 任何插件模块。"""

from __future__ import annotations

import logging

from .plugin_base import BasePlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """按 ``format_name`` 查找插件。"""

    def __init__(self) -> None:
        self._plugins: dict[str, BasePlugin] = {}

    def register_plugin(self, plugin: BasePlugin) -> None:
        """遍历 ``plugin.format_names`` 注册；重复注册抛 ``ValueError``。"""

        for format_name in plugin.format_names:
            if format_name in self._plugins:
                raise ValueError(f"格式 {format_name!r} 已注册")
        for format_name in plugin.format_names:
            self._plugins[format_name] = plugin
        logger.info("已注册插件 %s: %s", type(plugin).__name__, ",".join(plugin.format_names))

    def get(self, format_name: str) -> BasePlugin | None:
        """查找插件；未注册返回 ``None``。"""

        return self._plugins.get(format_name)

    def list_plugins(self) -> dict[str, BasePlugin]:
        """返回 ``format_name -> plugin`` 的副本。"""

        return dict(self._plugins)
