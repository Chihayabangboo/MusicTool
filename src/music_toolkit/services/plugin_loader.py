"""内置插件加载器。

插件发现只发生在这里：``core.registry`` 不 import 插件，GUI 也不直接 import 插件。
"""

from __future__ import annotations

import logging

from ..core.registry import PluginRegistry

logger = logging.getLogger(__name__)


def load_builtin_plugins(registry: PluginRegistry) -> PluginRegistry:
    """显式导入并注册四个内置插件，返回同一个 registry。"""

    from ..plugins.builtin_audio import BuiltinAudioPlugin
    from ..plugins.encrypted_detect_only import EncryptedDetectOnlyPlugin
    from ..plugins.encrypted_keyed import EncryptedKeyedPlugin
    from ..plugins.encrypted_offline import EncryptedOfflinePlugin

    registry.register_plugin(BuiltinAudioPlugin())
    registry.register_plugin(EncryptedOfflinePlugin())
    registry.register_plugin(EncryptedKeyedPlugin())
    registry.register_plugin(EncryptedDetectOnlyPlugin())
    logger.info("内置插件加载完成")
    return registry
