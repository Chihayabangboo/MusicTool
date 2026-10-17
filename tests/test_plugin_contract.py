from __future__ import annotations

import pytest

from music_toolkit.core.errors import MissingKey, UnsupportedFormat
from music_toolkit.core.models import SupportLevel
from music_toolkit.core.plugin_base import BasePlugin
from music_toolkit.plugins.builtin_audio import BuiltinAudioPlugin
from music_toolkit.plugins.encrypted_detect_only import EncryptedDetectOnlyPlugin
from music_toolkit.plugins.encrypted_keyed import EncryptedKeyedPlugin
from music_toolkit.plugins.encrypted_offline import EncryptedOfflinePlugin


def test_all_builtin_plugins_are_contract_compliant():
    plugins = [
        BuiltinAudioPlugin(),
        EncryptedOfflinePlugin(),
        EncryptedKeyedPlugin(),
        EncryptedDetectOnlyPlugin(),
    ]
    for plugin in plugins:
        assert isinstance(plugin, BasePlugin)
        assert plugin.format_names
        assert isinstance(plugin.support_level, SupportLevel)
        assert all(isinstance(name, str) and name for name in plugin.format_names)


def test_encrypted_offline_raises_unsupported(tmp_path):
    with pytest.raises(UnsupportedFormat):
        EncryptedOfflinePlugin().convert(tmp_path / "a.ncm", tmp_path / "b.mp3")


def test_encrypted_keyed_requires_key(tmp_path):
    with pytest.raises(MissingKey):
        EncryptedKeyedPlugin().convert(tmp_path / "a.kgg", tmp_path / "b.mp3", key=None)
    with pytest.raises(UnsupportedFormat):
        EncryptedKeyedPlugin().convert(tmp_path / "a.kgg", tmp_path / "b.mp3", key=b"x")


def test_encrypted_detect_only_raises_unsupported(tmp_path):
    with pytest.raises(UnsupportedFormat):
        EncryptedDetectOnlyPlugin().convert(tmp_path / "a.mgg1", tmp_path / "b.mp3")


def test_builtin_audio_format_names_and_level():
    plugin = BuiltinAudioPlugin()
    assert plugin.format_names == ("wav", "flac", "mp3", "ogg")
    assert plugin.support_level is SupportLevel.OFFLINE
