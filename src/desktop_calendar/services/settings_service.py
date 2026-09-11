import copy
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

DEFAULTS = {
    "window": {"x": 80, "y": 80, "width": 490, "height": 640, "opacity": 0.96},
    "theme": "dark",
    "background": "",
    "font_size": 10,
    "event_limit": 3,
    "first_weekday": 0,
    "sync_minutes": 5,
    "startup": False,
    "calendar_ids": None,
    "calendars": [],
    "client_file": "",
}


class SettingsService:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        config = copy.deepcopy(DEFAULTS)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return config
            for key in config:
                if key != "window" and key in data:
                    config[key] = data[key]
            if isinstance(data.get("window"), dict):
                config["window"].update(
                    {k: v for k, v in data["window"].items() if k in config["window"]}
                )
        except (OSError, ValueError):
            return config
        for key, low, high in [
            ("font_size", 8, 18),
            ("event_limit", 1, 5),
            ("sync_minutes", 1, 60),
        ]:
            value = config[key]
            config[key] = min(high, max(low, value)) if type(value) is int else DEFAULTS[key]
        for key, low, high in [
            ("width", 350, 4000),
            ("height", 420, 4000),
            ("x", -100000, 100000),
            ("y", -100000, 100000),
            ("opacity", 0.35, 1.0),
        ]:
            value = config["window"][key]
            config["window"][key] = (
                min(high, max(low, value))
                if isinstance(value, (int, float))
                else DEFAULTS["window"][key]
            )
        if config["theme"] not in ("dark", "light"):
            config["theme"] = "dark"
        if config["first_weekday"] not in (0, 6):
            config["first_weekday"] = 0
        for key in ("client_file", "background"):
            if not isinstance(config[key], str):
                config[key] = ""
        if not isinstance(config["calendars"], list):
            config["calendars"] = []
        config["calendars"] = [
            c for c in config["calendars"] if isinstance(c, dict) and isinstance(c.get("id"), str)
        ]
        if config["calendar_ids"] is not None:
            if not isinstance(config["calendar_ids"], list):
                config["calendar_ids"] = None
            else:
                config["calendar_ids"] = [c for c in config["calendar_ids"] if isinstance(c, str)]
        config["startup"] = config["startup"] is True
        return config

    def save(self, config: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(config, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
