from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo


def visible_dates(month: date, first_weekday: int = 0) -> list[date]:
    first = month.replace(day=1)
    start = first - timedelta(days=(first.weekday() - first_weekday) % 7)
    return [start + timedelta(days=i) for i in range(42)]


@dataclass(frozen=True)
class Event:
    calendar_id: str
    google_event_id: str
    title: str
    start_time: str
    end_time: str
    all_day: bool
    location: str = ""
    status: str = "confirmed"
    updated_at: str = ""
    color: str = "#78a9ff"

    @classmethod
    def from_google(cls, calendar_id: str, item: dict, color: str = "#78a9ff") -> "Event":
        start, end = item["start"], item["end"]
        all_day = "date" in start
        return cls(
            calendar_id,
            item["id"],
            item.get("summary", "(제목 없음)"),
            start["date" if all_day else "dateTime"],
            end["date" if all_day else "dateTime"],
            all_day,
            item.get("location", ""),
            item.get("status", "confirmed"),
            item.get("updated", ""),
            color,
        )

    def occurs_on(self, day: date, zone: tzinfo) -> bool:
        if self.status == "cancelled":
            return False
        if self.all_day:
            return date.fromisoformat(self.start_time) <= day < date.fromisoformat(self.end_time)
        start = datetime.fromisoformat(self.start_time).astimezone(zone)
        end = datetime.fromisoformat(self.end_time).astimezone(zone)
        lower = datetime.combine(day, time.min, zone)
        upper = datetime.combine(day + timedelta(days=1), time.min, zone)
        return start < upper and (end > lower or start == end and lower <= start)

    def label(self, zone: tzinfo) -> str:
        if self.all_day:
            return self.title
        return f"{datetime.fromisoformat(self.start_time).astimezone(zone):%H:%M} {self.title}"
