from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.settings_service import SettingsService
from desktop_calendar.ui.main_window import MainWindow


@pytest.fixture
def window(app, tmp_path):
    widget = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        Mock(),
        auto_sync=False,
    )
    widget.setGeometry(120, 80, 520, 620)
    widget.reveal()
    app.processEvents()
    yield widget
    widget.lower_timer.stop()
    widget.clock_timer.stop()
    widget.save_timer.stop()
    widget.tray.hide()
    widget.quitting = True
    widget.close()
    app.processEvents()


def drag(window, point, delta):
    target = window.childAt(point) or window
    start = target.mapFrom(window, point)
    QTest.mousePress(target, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(target, start + delta, delay=30)
    QTest.mouseRelease(target, Qt.MouseButton.LeftButton, pos=start + delta)


@pytest.mark.parametrize(
    "edge,delta",
    [
        ("bottom", QPoint(0, 70)),
        ("right", QPoint(70, 0)),
        ("corner", QPoint(50, 60)),
        ("left", QPoint(-40, 0)),
        ("top", QPoint(0, -30)),
    ],
)
def test_drag_edges_changes_size(window, app, edge, delta):
    before = window.geometry()
    points = {
        "bottom": QPoint(window.width() // 2, window.height() - 2),
        "right": QPoint(window.width() - 2, window.height() // 2),
        "corner": QPoint(window.width() - 2, window.height() - 2),
        "left": QPoint(2, window.height() // 2),
        "top": QPoint(window.width() // 2, 2),
    }
    drag(window, points[edge], delta)
    app.processEvents()
    assert window.width() == before.width() + abs(delta.x())
    assert window.height() == before.height() + abs(delta.y())
    if edge == "left":
        assert window.geometry().right() == before.right()
    if edge == "top":
        assert window.geometry().bottom() == before.bottom()


def test_drag_size_is_saved_and_restored(window, app):
    drag(window, QPoint(window.width() // 2, window.height() - 2), QPoint(0, 60))
    QTest.qWait(500)
    saved = window.settings.load()["window"]
    assert saved["height"] == window.height() == 680
    restored = MainWindow(window.settings, window.repository, Mock(), auto_sync=False)
    try:
        # A small/high-DPI CI desktop must apply the app's monitor recovery policy.
        screen_height = app.primaryScreen().availableGeometry().height()
        assert restored.height() == min(680, screen_height)
    finally:
        restored.tray.hide()
        restored.quitting = True
        restored.close()
        app.processEvents()


def test_drag_cannot_shrink_below_minimum(window, app):
    drag(window, QPoint(window.width() - 2, window.height() - 2), QPoint(-2000, -2000))
    app.processEvents()
    assert window.width() >= window.minimumWidth()
    assert window.height() >= window.minimumHeight()
    assert window.width() < 520
    assert window.height() < 620
