import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import date
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

from desktop_calendar.models.event import Event
from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.settings_service import SettingsService
from desktop_calendar.ui.calendar_widget import CalendarWidget
from desktop_calendar.ui.main_window import MainWindow
from desktop_calendar.ui.settings_dialog import SettingsDialog


def test_tray_reveal_does_not_queue_lowering(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        Mock(),
        auto_sync=False,
    )
    try:
        with patch("desktop_calendar.ui.main_window.lower_window") as lower:
            window.reveal()
            app.processEvents()
            QTest.qWait(350)
            lower.assert_not_called()
    finally:
        window.tray.hide()
        window.quitting = True
        window.close()


def test_settings_dialog_protects_parent_from_periodic_lowering(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        Mock(),
        auto_sync=False,
    )
    dialog = QDialog(window)
    try:
        window.reveal()
        dialog.show()
        app.processEvents()
        with (
            patch.object(window, "isActiveWindow", return_value=False),
            patch("desktop_calendar.ui.main_window.lower_window") as lower,
        ):
            window.tick()
            lower.assert_not_called()
    finally:
        dialog.close()
        window.tray.hide()
        window.quitting = True
        window.close()


def test_calendar_has_42_cells_and_overflow(tmp_path):
    app = QApplication.instance() or QApplication([])
    widget = CalendarWidget()
    config = SettingsService(tmp_path / "config.json").load()
    config["event_limit"] = 2
    items = [Event("a", str(i), f"일정{i}", "2026-09-02", "2026-09-03", True) for i in range(5)]
    widget.render(date(2026, 9, 1), items, config, ZoneInfo("Asia/Seoul"))
    assert len(widget.cells) == 42
    cell = next(c for c in widget.cells if c.day == date(2026, 9, 2))
    assert cell.more.text() == "+3"
    assert len(cell.events) == 5
    widget.show()
    widget.render(date(2026, 10, 1), [], config, ZoneInfo("Asia/Seoul"))
    assert cell.isHidden()
    widget.close()
    app.processEvents()


def test_delayed_lowering_rechecks_focus_and_preserves_idle_behavior(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        Mock(),
        auto_sync=False,
    )
    try:
        window.reveal()
        app.processEvents()
        with patch("desktop_calendar.ui.main_window.lower_window") as lower:
            with patch.object(window, "isActiveWindow", return_value=True):
                window.lower_timer.start()
                QTest.qWait(350)
                lower.assert_not_called()
            with patch.object(window, "isActiveWindow", return_value=False):
                window.lower_if_idle()
                lower.assert_called_once_with(int(window.winId()))
    finally:
        window.tray.hide()
        window.quitting = True
        window.close()


def test_window_restores_geometry_and_month_navigation(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = SettingsService(tmp_path / "config.json")
    window = MainWindow(settings, EventRepository(tmp_path / "cache.db"), Mock(), auto_sync=False)
    window.refresh = Mock()
    window.month = date(2026, 12, 1)
    window.change_month(1)
    assert window.month == date(2027, 1, 1)
    window.move(100, 110)
    window.resize(530, 680)
    window.save_geometry()
    assert settings.load()["window"]["width"] == 530
    window.tray.hide()
    window.quitting = True
    window.close()
    app.processEvents()


def test_worker_offline_error_keeps_app_alive(tmp_path):
    app = QApplication.instance() or QApplication([])
    auth = Mock()
    auth.api.side_effect = OSError("do-not-display-secret")
    window = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        auth,
        auto_sync=False,
    )
    window.refresh()
    timer = QElapsedTimer()
    timer.start()
    while window.worker is not None and timer.elapsed() < 5000:
        app.processEvents()
        QTest.qWait(5)
    assert window.worker is None
    assert "캐시" in window.status.text()
    assert "do-not-display-secret" not in window.status.text()
    window.tray.hide()
    window.quitting = True
    window.close()


def test_settings_can_select_no_calendars(tmp_path):
    app = QApplication.instance() or QApplication([])
    config = SettingsService(tmp_path / "config.json").load()
    config["calendars"] = [{"id": "a", "summary": "내 일정"}]
    config["calendar_ids"] = []
    dialog = SettingsDialog(config)
    assert not hasattr(dialog, "client_file")
    assert any("Google 로그인" in button.text() for button in dialog.findChildren(QPushButton))
    dialog.finish("save")
    assert dialog.config["calendar_ids"] == []
    dialog.close()
    app.processEvents()
