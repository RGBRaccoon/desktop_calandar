from desktop_calendar.models.event import Event


class GoogleCalendarService:
    def __init__(self, api):
        self.api = api

    def calendars(self) -> list[dict]:
        result = []
        token = None
        while True:
            page = self.api.calendarList().list(pageToken=token, minAccessRole="reader").execute()
            result.extend(
                {
                    "id": item["id"],
                    "summary": item.get("summary", item["id"]),
                    "color": item.get("backgroundColor", "#78a9ff"),
                    "primary": item.get("primary", False),
                }
                for item in page.get("items", [])
            )
            token = page.get("nextPageToken")
            if not token:
                return result

    def events(
        self, calendar_id: str, lower: str, upper: str, color: str = "#78a9ff"
    ) -> list[Event]:
        result = []
        token = None
        while True:
            page = (
                self.api.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=lower,
                    timeMax=upper,
                    singleEvents=True,
                    showDeleted=False,
                    orderBy="startTime",
                    maxResults=2500,
                    pageToken=token,
                )
                .execute()
            )
            result.extend(
                Event.from_google(calendar_id, item, color)
                for item in page.get("items", [])
                if item.get("status") != "cancelled"
            )
            token = page.get("nextPageToken")
            if not token:
                return result
