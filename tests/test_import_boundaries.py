from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

BANNED = ("ttkbootstrap", "tkinter", "tkinterdnd2", "PySide6", "PyQt5", "PyQt6")
SRC = Path(__file__).resolve().parents[1] / "src" / "music_toolkit"


def _imported_modules(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_core_and_services_have_no_gui_imports():
    offenders = []
    for package in ("core", "services"):
        for path in (SRC / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_modules(tree):
                if any(module == name or module.startswith(name + ".") for name in BANNED):
                    offenders.append((str(path.relative_to(SRC)), module))
    assert offenders == []


def test_gui_only_imports_services():
    offenders = []
    for path in (SRC / "gui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for module in _imported_modules(tree):
            parts = module.lstrip(".").split(".")
            if "core" in parts or "plugins" in parts:
                offenders.append((str(path.relative_to(SRC)), module))
    assert offenders == []


def test_core_and_services_do_not_import_gui():
    offenders = []
    for package in ("core", "services"):
        for path in (SRC / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for module in _imported_modules(tree):
                parts = module.lstrip(".").split(".")
                if any(part in {"gui", "ttkbootstrap", "tkinter", "tkinterdnd2"} for part in parts):
                    offenders.append((str(path.relative_to(SRC)), module))
    assert offenders == []


def test_runtime_does_not_load_gui_modules():
    code = f"""
import json, sys
import music_toolkit.core
import music_toolkit.services
banned = {BANNED!r}
loaded = sorted(
    name for name in sys.modules
    if any(name == b or name.startswith(b + '.') for b in banned)
)
print(json.dumps(loaded))
"""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC.parent) + os.pathsep + env.get("PYTHONPATH", "")
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    loaded = json.loads(completed.stdout.strip())
    assert loaded == []
