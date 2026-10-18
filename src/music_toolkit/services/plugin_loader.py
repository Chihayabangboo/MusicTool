"""内置插件加载器。"""
from __future__ import annotations

import logging
from ..core.registry import PluginRegistry

# 导入新拆分的插件
from ..plugins.builtin_audio import BuiltinAudioPlugin
from ..plugins.ncm_plugin import NcmPlugin
from ..plugins.qmc_plugin import QmcPlugin
from ..plugins.kgm_plugin import KgmPlugin

logger = logging.getLogger(__name__)

def load_builtin_plugins(registry: PluginRegistry) -> PluginRegistry:
    """显式导入并注册所有的内置插件，返回同一个 registry。"""
    
    # 注册普通音频插件
    registry.register_plugin(BuiltinAudioPlugin())
    
    # 注册加密解密插件（按格式拆分）
    registry.register_plugin(NcmPlugin())   # 网易云 .ncm
    registry.register_plugin(QmcPlugin())   # QQ音乐 .qmc / .mflac
    registry.register_plugin(KgmPlugin())   # 酷狗 .kgm
    
    logger.info("内置插件加载完成")
    return registry