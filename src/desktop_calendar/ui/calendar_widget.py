from datetime import date, datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from desktop_calendar.models.event import Event, visible_dates


class DayCell(QFrame):
    selected = Signal(object)

    def __init__(self, day, events, month, config, zone):
        super().__init__()
        self.day, self.events = day, events
        self.setObjectName("dayCell")
        self.setProperty("outside", day.month != month.month)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 5, 4, 4)
        layout.setSpacing(3)
        number = QLabel(str(day.day))
        number.setObjectName("today" if day == datetime.now(zone).date() else "dayNumber")
        layout.addWidget(number)
        for item in events[: config["event_limit"]]:
            label = QLabel(item.label(zone))
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setMinimumWidth(0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            color = item.color if QColor(item.color).isValid() else "#78a9ff"
            label.setStyleSheet(f"color: {color}; background: transparent;")
            label.setToolTip(item.label(zone))
            layout.addWidget(label)
        self.more = QLabel(
            f"+{len(events) - config['event_limit']}" if len(events) > config["event_limit"] else ""
        )
        self.more.setObjectName("muted")
        layout.addWidget(self.more)
        layout.addStretch()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self)
        super().mousePressEvent(event)


class CalendarWidget(QWidget):
    day_selected = Signal(object)

    def __init__(self):
        super().__init__()
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(1)
        self.cells = []

    def render(self, month: date, events: list[Event], config: dict, zone: ZoneInfo):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.hide()
                widget.deleteLater()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        for col in range(7):
            label = QLabel(weekdays[(config["first_weekday"] + col) % 7])
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setObjectName("weekday")
            self.grid.addWidget(label, 0, col)
            self.grid.setColumnStretch(col, 1)
        self.cells = []
        for i, day in enumerate(visible_dates(month, config["first_weekday"])):
            items = sorted(
                (e for e in events if e.occurs_on(day, zone)),
                key=lambda e: (not e.all_day, e.start_time, e.title),
            )
            cell = DayCell(day, items, month, config, zone)
            cell.selected.connect(self.day_selected.emit)
            self.cells.append(cell)
            self.grid.addWidget(cell, i // 7 + 1, i % 7)
            self.grid.setRowStretch(i // 7 + 1, 1)
