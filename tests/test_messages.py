from __future__ import annotations

from pathlib import Path

from music_toolkit.core.models import ScanItem, SupportLevel
from music_toolkit.services.messages import (
    CancelledMsg,
    FinishedMsg,
    LogMsg,
    MsgType,
    ScanBatchMsg,
    ScanDoneMsg,
    ScanStartMsg,
    TaskFailMsg,
    TaskOkMsg,
    TaskProgressMsg,
)


def test_all_messages_have_correct_type():
    item = ScanItem(Path("a.wav"), "wav", SupportLevel.OFFLINE, None, {}, None)
    messages = [
        (ScanStartMsg(3), MsgType.SCAN_START),
        (ScanBatchMsg([item]), MsgType.SCAN_BATCH),
        (ScanDoneMsg(3, 1, 0), MsgType.SCAN_DONE),
        (TaskProgressMsg("j1", 50, 1, 3), MsgType.TASK_PROGRESS),
        (TaskOkMsg("j1", Path("out.mp3")), MsgType.TASK_OK),
        (TaskFailMsg("j1", "bad"), MsgType.TASK_FAIL),
        (FinishedMsg(3, 2, 1), MsgType.FINISHED),
        (CancelledMsg(1), MsgType.CANCELLED),
        (LogMsg("INFO", "hello"), MsgType.LOG),
    ]
    for message, expected in messages:
        assert message.type is expected
        assert isinstance(message.type, MsgType)


def test_message_fields():
    message = TaskProgressMsg(job_id="j1", percent=42, overall_done=1, overall_total=4)
    assert (message.job_id, message.percent, message.overall_done, message.overall_total) == (
        "j1",
        42,
        1,
        4,
    )
