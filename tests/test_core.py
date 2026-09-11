from datetime import date
from zoneinfo import ZoneInfo

from desktop_calendar.models.event import Event, visible_dates
from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.settings_service import SettingsService


def event(event_id="one", title="회의"):
    return Event.from_google(
        "primary",
        {
            "id": event_id,
            "summary": title,
            "start": {"date": "2026-09-02"},
            "end": {"date": "2026-09-04"},
        },
    )


def test_all_day_end_is_exclusive():
    item = event()
    assert item.occurs_on(date(2026, 9, 2), ZoneInfo("Asia/Seoul"))
    assert item.occurs_on(date(2026, 9, 3), ZoneInfo("Asia/Seoul"))
    assert not item.occurs_on(date(2026, 9, 4), ZoneInfo("Asia/Seoul"))


def test_timed_event_converts_timezone():
    item = Event.from_google(
        "a",
        {
            "id": "x",
            "start": {"dateTime": "2026-09-02T23:00:00Z"},
            "end": {"dateTime": "2026-09-03T01:00:00Z"},
        },
    )
    assert not item.occurs_on(date(2026, 9, 2), ZoneInfo("Asia/Seoul"))
    assert item.occurs_on(date(2026, 9, 3), ZoneInfo("Asia/Seoul"))


def test_visible_grid_always_six_weeks():
    days = visible_dates(date(2026, 9, 1), 0)
    assert len(days) == 42
    assert days[0] == date(2026, 8, 31)


def test_snapshot_replaces_deleted_events_and_persists(tmp_path):
    path = tmp_path / "calendar.db"
    repo = EventRepository(path)
    repo.replace("range", [event()], "2026-09-01T12:00:00+00:00")
    assert EventRepository(path).load("range")[0][0].title == "회의"
    repo.replace("range", [], "later")
    assert repo.load("range") == ([], "later")


def test_settings_invalid_values_and_atomic_save(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"window":{"width":-1},"sync_minutes":0,"theme":"bad"}')
    service = SettingsService(path)
    config = service.load()
    assert config["window"]["width"] >= 350
    assert config["sync_minutes"] >= 1
    assert config["theme"] == "dark"
    config["theme"] = "light"
    service.save(config)
    assert service.load()["theme"] == "light"


def test_corrupt_settings(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{bad")
    assert SettingsService(path).load()["sync_minutes"] == 5
