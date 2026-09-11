import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
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
                "CREATE TABLE IF NOT EXISTS snapshots (range_key TEXT PRIMARY KEY, payload TEXT NOT NULL, synced_at TEXT NOT NULL)"
            )

    def replace(self, key: str, events: list[Event], synced_at: str):
        payload = json.dumps([asdict(e) for e in events], ensure_ascii=False)
        with self.connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?)", (key, payload, synced_at)
            )

    def load(self, key: str) -> tuple[list[Event], str]:
        with self.connection() as db:
            row = db.execute(
                "SELECT payload, synced_at FROM snapshots WHERE range_key=?", (key,)
            ).fetchone()
        if row is None:
            return [], ""
        return [Event(**item) for item in json.loads(row[0])], row[1]

    def clear(self):
        with self.connection() as db:
            db.execute("PRAGMA secure_delete=ON")
            db.execute("DELETE FROM snapshots")
