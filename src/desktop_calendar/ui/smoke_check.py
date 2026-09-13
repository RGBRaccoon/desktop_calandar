"""Offline UI checks executed inside the packaged EXE, using isolated test data."""

from datetime import date
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter
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
    source = window.settings.path.parent / "smoke-background.png"
    test_image = QImage(160, 90, QImage.Format.Format_RGB32)
    painter = QPainter(test_image)
    painter.fillRect(0, 0, 80, 90, QColor("#347590"))
    painter.fillRect(80, 0, 80, 90, QColor("#8f4f67"))
    painter.end()
    if not test_image.save(str(source)):
        raise AssertionError("Background fixture write failed")

    def dismiss():
        dialog = QApplication.activeModalWidget()
        observed.append(isinstance(dialog, SettingsDialog) and dialog.isVisible())
        if isinstance(dialog, SettingsDialog):
            dialog.config["background_image"] = str(source)
            dialog.image_opacity.setValue(0.8)
            dialog.image_brightness.setValue(0.7)
            dialog.finish("save")
        elif dialog:
            dialog.close()

    QTimer.singleShot(100, dismiss)
    QTest.mouseClick(window.settings_button, Qt.MouseButton.LeftButton)
    if observed != [True] or not window.isVisible():
        raise AssertionError("Settings interaction failed")
    saved_image = Path(window.settings.load()["background_image"])
    if saved_image == source or not saved_image.is_file():
        raise AssertionError("Background was not imported")
    source.unlink()
    window.apply_appearance()
    if window.background_image.isNull():
        raise AssertionError("Background did not survive source removal")
    QTest.qWait(100)
    if not all(
        cell.isVisible() and cell.width() > 0 and cell.height() > 0
        for cell in window.calendar.cells
    ):
        raise AssertionError("Calendar cells disappeared after background update")
    screen = window.screen()
    if screen is not None:
        capture = screen.grabWindow(int(window.winId())).toImage()
        scale_x = capture.width() / window.width()
        scale_y = capture.height() / window.height()
        origin = window.title.mapTo(window, QPoint(0, 0))
        left = max(0, int(origin.x() * scale_x))
        top = max(0, int(origin.y() * scale_y))
        right = min(capture.width(), int((origin.x() + window.title.width()) * scale_x))
        bottom = min(capture.height(), int((origin.y() + window.title.height()) * scale_y))
        light_pixels = sum(
            1
            for y in range(top, bottom)
            for x in range(left, right)
            if min(
                capture.pixelColor(x, y).red(),
                capture.pixelColor(x, y).green(),
                capture.pixelColor(x, y).blue(),
            )
            > 180
        )
        if light_pixels < 20:
            raise AssertionError("Background covered the month title")
    window.save_geometry()
    if window.settings.load()["window"]["height"] != window.height():
        raise AssertionError("Resize persistence failed")
