import sqlite3
from contextlib import contextmanager
from dataclasses import astuple
from datetime import UTC, datetime
from pathlib import Path

from desktop_calendar.models.event import Event


class EventRepository:
    """Independent connections per operation, safe for UI/worker use."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._initialize()
        except sqlite3.DatabaseError as error:
            if getattr(error, "sqlite_errorcode", None) not in (
                sqlite3.SQLITE_CORRUPT,
                sqlite3.SQLITE_NOTADB,
            ):
                raise
            # Preserve the damaged cache for diagnosis; never discard on a lock/IO error.
            path.rename(path.with_suffix(f".corrupt-{datetime.now(UTC):%Y%m%d%H%M%S}"))
            self._initialize()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def _initialize(self):
        with self.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS ranges (range_key TEXT PRIMARY KEY, synced_at TEXT NOT NULL)"
            )
            db.execute("""CREATE TABLE IF NOT EXISTS events (
                range_key TEXT NOT NULL, calendar_id TEXT NOT NULL, google_event_id TEXT NOT NULL,
                title TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                all_day INTEGER NOT NULL, location TEXT NOT NULL, status TEXT NOT NULL,
                updated_at TEXT NOT NULL, color TEXT NOT NULL,
                PRIMARY KEY(range_key, calendar_id, google_event_id))""")
            # Prototype snapshots are disposable caches; do not retain account data in an unused table.
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DROP TABLE IF EXISTS snapshots")

    def replace(self, key: str, events: list[Event], synced_at: str):
        with self.connection() as db:
            db.execute("DELETE FROM events WHERE range_key=?", (key,))
            db.executemany(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(key, *astuple(event)) for event in events],
            )
            db.execute("INSERT OR REPLACE INTO ranges VALUES (?, ?)", (key, synced_at))

    def load(self, key: str) -> tuple[list[Event], str]:
        with self.connection() as db:
            row = db.execute("SELECT synced_at FROM ranges WHERE range_key=?", (key,)).fetchone()
            rows = db.execute(
                "SELECT calendar_id, google_event_id, title, start_time, end_time, all_day, location, status, updated_at, color FROM events WHERE range_key=? ORDER BY all_day DESC, start_time, google_event_id",
                (key,),
            ).fetchall()
        if row is None:
            return [], ""
        return [Event(*item) for item in rows], row[0]

    def clear(self):
        with self.connection() as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM ranges")
