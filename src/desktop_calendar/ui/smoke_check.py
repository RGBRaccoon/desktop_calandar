"""Offline UI checks executed inside the packaged EXE, using isolated test data."""

from datetime import date

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from desktop_calendar.ui.settings_dialog import SettingsDialog


def check_interactions(window):
    # Navigation normally starts a sync; this smoke check must not contact Google.
    window.refresh = lambda: None
    window.hide()
    window.tray.contextMenu().actions()[0].trigger()
    QTest.qWait(50)
    if not window.isVisible() or len(window.calendar.cells) != 42:
        raise AssertionError("Tray restoration/calendar rendering failed")
    window.month = date(2026, 12, 1)
    button = next(b for b in window.findChildren(QPushButton) if b.toolTip() == "다음 달")
    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    if window.month != date(2027, 1, 1):
        raise AssertionError("Month navigation failed")
    before = window.height()
    point = QPoint(window.width() // 2, window.height() - 2)
    target = window.childAt(point)
    if target is None:
        raise AssertionError("Resize hit target missing")
    start = target.mapFrom(window, point)
    QTest.mousePress(target, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(target, start + QPoint(0, 30), delay=30)
    QTest.mouseRelease(target, Qt.MouseButton.LeftButton, pos=start + QPoint(0, 30))
    if window.height() != before + 30:
        raise AssertionError("Bottom edge drag failed")
    observed = []

    def dismiss():
        dialog = QApplication.activeModalWidget()
        observed.append(isinstance(dialog, SettingsDialog) and dialog.isVisible())
        if dialog:
            dialog.close()

    QTimer.singleShot(100, dismiss)
    QTest.mouseClick(window.settings_button, Qt.MouseButton.LeftButton)
    if observed != [True] or not window.isVisible():
        raise AssertionError("Settings interaction failed")
    window.save_geometry()
    if window.settings.load()["window"]["height"] != window.height():
        raise AssertionError("Resize persistence failed")
