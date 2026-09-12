from datetime import date
from unittest.mock import Mock

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.settings_service import SettingsService
from desktop_calendar.ui.main_window import MainWindow
from desktop_calendar.ui.settings_dialog import SettingsDialog


def test_tray_restore_month_buttons_and_settings_click(app, tmp_path):
    window = MainWindow(
        SettingsService(tmp_path / "config.json"),
        EventRepository(tmp_path / "cache.db"),
        Mock(),
        auto_sync=False,
    )
    window.refresh = Mock()
    observations = []
    try:
        window.hide()
        window.tray.contextMenu().actions()[0].trigger()
        app.processEvents()
        assert window.isVisible()
        window.month = date(2026, 12, 1)
        next_button = next(b for b in window.findChildren(QPushButton) if b.toolTip() == "다음 달")
        QTest.mouseClick(next_button, Qt.MouseButton.LeftButton)
        assert window.month == date(2027, 1, 1)

        def inspect_and_close():
            dialog = QApplication.activeModalWidget()
            observations.append(isinstance(dialog, SettingsDialog) and dialog.isVisible())
            observations.append(window.isVisible())
            if dialog:
                dialog.close()

        QTimer.singleShot(100, inspect_and_close)
        QTest.mouseClick(window.settings_button, Qt.MouseButton.LeftButton)
        assert observations == [True, True]
        assert window.isVisible()
    finally:
        window.tray.hide()
        window.quitting = True
        window.close()
