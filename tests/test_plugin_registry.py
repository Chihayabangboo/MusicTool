from __future__ import annotations

import pytest

from music_toolkit.core.errors import MusicToolkitError
from music_toolkit.core.models import SupportLevel
from music_toolkit.core.plugin_base import BasePlugin
from music_toolkit.core.registry import PluginRegistry


class DummyPlugin(BasePlugin):
    format_names = ("a", "b")
    support_level = SupportLevel.OFFLINE

    def convert(self, src, dst, cancel_event=None, key=None):
        return None


class OtherPlugin(DummyPlugin):
    format_names = ("b",)


def test_register_lookup_and_list():
    registry = PluginRegistry()
    plugin = DummyPlugin()
    registry.register_plugin(plugin)
    assert registry.get("a") is plugin
    assert registry.get("b") is plugin
    assert registry.get("missing") is None
    listed = registry.list_plugins()
    assert set(listed) == {"a", "b"}
    listed.clear()
    assert registry.get("a") is plugin


def test_duplicate_registration_raises():
    registry = PluginRegistry()
    registry.register_plugin(DummyPlugin())
    with pytest.raises(ValueError):
        registry.register_plugin(OtherPlugin())


def test_errors_carry_message():
    error = MusicToolkitError("消息")
    assert str(error) == "消息"
    assert error.message == "消息"
