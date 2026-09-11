import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from desktop_calendar.repositories.event_repository import EventRepository


class SyncService:
    def __init__(self, repository: EventRepository):
        self.repository = repository

    @staticmethod
    def key(days: list[date], calendar_ids: list[str], zone: str) -> str:
        return json.dumps([str(days[0]), str(days[-1]), sorted(calendar_ids), zone])

    def sync(self, provider, days: list[date], calendars: list[dict], zone: ZoneInfo) -> str:
        lower = datetime.combine(days[0], time.min, zone).isoformat()
        upper = datetime.combine(days[-1] + timedelta(days=1), time.min, zone).isoformat()
        events = []
        for calendar in calendars:
            events.extend(
                provider.events(calendar["id"], lower, upper, calendar.get("color", "#78a9ff"))
            )
        key = self.key(days, [c["id"] for c in calendars], str(zone))
        # Commit only once every page and calendar has succeeded.
        self.repository.replace(key, events, datetime.now(UTC).isoformat())
        return key
