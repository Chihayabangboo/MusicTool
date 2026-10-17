from __future__ import annotations

from music_toolkit.services.app_factory import AppContext, bootstrap_app
from music_toolkit.services.metadata_service import MetadataService
from music_toolkit.services.output_planner import OutputPlanner
from music_toolkit.services.scan_service import ScanService
from music_toolkit.services.task_service import TaskService


def test_app_context_has_all_fields():
    app = bootstrap_app()
    assert isinstance(app, AppContext)
    assert app.registry is not None
    assert app.detector is not None
    assert isinstance(app.metadata_service, MetadataService)
    assert isinstance(app.scan_service, ScanService)
    assert isinstance(app.task_service, TaskService)
    assert callable(app.planner_factory)
    planner = app.planner_factory(__import__("pathlib").Path("."), "mp3", True, False)
    assert isinstance(planner, OutputPlanner)


def test_all_builtin_plugins_registered():
    app = bootstrap_app()
    registered = set(app.registry.list_plugins())
    expected = {
        "wav",
        "flac",
        "mp3",
        "ogg",
        "ncm",
        "qmc1",
        "qmc2",
        "kgm",
        "kgma",
        "vpr",
        "kwm",
        "kgg",
        "qmc3",
    }
    assert registered == expected


def test_two_bootstraps_are_independent():
    first = bootstrap_app()
    second = bootstrap_app()
    assert first.registry is not second.registry
    assert first.registry.list_plugins().keys() == second.registry.list_plugins().keys()
    first.registry.list_plugins()["wav"] = None
    assert second.registry.get("wav") is not None
