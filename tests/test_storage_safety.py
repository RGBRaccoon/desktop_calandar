import sqlite3

import pytest

from desktop_calendar.models.event import Event
from desktop_calendar.repositories.event_repository import EventRepository


def test_failed_transaction_rolls_back_previous_events(tmp_path):
    repo = EventRepository(tmp_path / "calendar.db")
    old = Event("a", "old", "기존", "2026-09-01", "2026-09-02", True)
    new = Event("a", "new", "새 일정", "2026-09-01", "2026-09-02", True)
    repo.replace("range", [old], "previous")
    with pytest.raises(sqlite3.IntegrityError):
        repo.replace("range", [new, new], "new")
    assert repo.load("range") == ([old], "previous")


def test_corrupt_database_is_preserved_and_recreated(tmp_path):
    path = tmp_path / "calendar.db"
    path.write_bytes(b"broken database")
    repo = EventRepository(path)
    assert repo.load("range") == ([], "")
    assert len(list(tmp_path.glob("*.corrupt-*"))) == 1


def test_logout_clear_removes_all_ranges(tmp_path):
    repo = EventRepository(tmp_path / "calendar.db")
    event = Event("a", "private", "private-title", "2026-09-01", "2026-09-02", True)
    repo.replace("a", [event], "time")
    repo.replace("b", [event], "time")
    repo.clear()
    assert repo.load("a") == ([], "")
    assert repo.load("b") == ([], "")
    assert b"private-title" not in (tmp_path / "calendar.db").read_bytes()
