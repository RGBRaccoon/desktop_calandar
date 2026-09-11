from datetime import date
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from desktop_calendar.infrastructure.windows_api import fit_geometry, startup_command
from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.calendar_service import GoogleCalendarService
from desktop_calendar.services.google_auth_service import GoogleAuthService, LoginRequired
from desktop_calendar.services.sync_service import SyncService


def test_pages_and_recurring_query():
    api = Mock()
    api.events().list().execute.side_effect = [
        {
            "items": [
                {"id": "one", "start": {"date": "2026-09-01"}, "end": {"date": "2026-09-02"}}
            ],
            "nextPageToken": "next",
        },
        {"items": []},
    ]
    result = GoogleCalendarService(api).events("a", "lo", "hi")
    assert len(result) == 1
    assert api.events().list.call_args.kwargs["pageToken"] == "next"
    assert api.events().list.call_args.kwargs["singleEvents"] is True


def test_sync_failure_preserves_snapshot(tmp_path):
    repo = EventRepository(tmp_path / "cache.db")
    provider = Mock()
    service = SyncService(repo)
    days = [date(2026, 9, 1), date(2026, 9, 30)]
    key = service.key(days, ["a", "b"], "Asia/Seoul")
    repo.replace(key, [], "previous")
    provider.events.side_effect = [[], OSError("offline")]
    with pytest.raises(OSError):
        service.sync(provider, days, [{"id": "a"}, {"id": "b"}], ZoneInfo("Asia/Seoul"))
    assert repo.load(key) == ([], "previous")


def test_auth_without_credentials_does_not_open_browser():
    store = Mock()
    store.load.return_value = None
    with pytest.raises(LoginRequired):
        GoogleAuthService(store).credentials()


def test_expired_credentials_refresh_and_store():
    store = Mock()
    store.load.return_value = {"token": "x"}
    credentials = Mock(valid=False, expired=True, refresh_token="refresh")
    credentials.to_json.return_value = '{"token":"new"}'
    auth = GoogleAuthService(store, credential_factory=lambda data: credentials)
    assert auth.credentials() is credentials
    credentials.refresh.assert_called_once()
    store.save.assert_called_once_with({"token": "new"})


def test_geometry_recovers_disconnected_monitor():
    assert fit_geometry((3000, 0, 490, 640), [(0, 0, 1920, 1080)]) == (40, 40, 490, 640)
    assert fit_geometry((-1200, 40, 490, 640), [(0, 0, 1920, 1080), (-1920, 0, 1920, 1080)]) == (
        -1200,
        40,
        490,
        640,
    )


def test_startup_command_quotes_paths():
    assert startup_command("C:/Program Files/app.exe") == '"C:/Program Files/app.exe"'
