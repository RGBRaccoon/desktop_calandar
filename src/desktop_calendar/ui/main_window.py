import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from tzlocal import get_localzone

from desktop_calendar.infrastructure.windows_api import fit_geometry, lower_window
from desktop_calendar.models.event import visible_dates
from desktop_calendar.services.background_service import (
    import_background,
    read_background,
    remove_managed_background,
)
from desktop_calendar.services.calendar_service import GoogleCalendarService
from desktop_calendar.services.google_auth_service import LoginRequired
from desktop_calendar.services.oauth_config import OAuthConfigurationError, load_client_config
from desktop_calendar.services.startup_service import StartupService
from desktop_calendar.services.sync_service import SyncService
from desktop_calendar.ui.calendar_widget import CalendarWidget
from desktop_calendar.ui.resize_handles import ResizeHandles
from desktop_calendar.ui.settings_dialog import SettingsDialog

logger = logging.getLogger("desktop_calendar")


class BackgroundCanvas(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.color = QColor("#151c27")
        self.image = QImage()
        self.opacity = 0.8
        self.brightness = 0.6
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.color)
        if self.image.isNull():
            return
        scale = max(self.width() / self.image.width(), self.height() / self.image.height())
        width, height = self.width() / scale, self.height() / scale
        source = QRectF(
            (self.image.width() - width) / 2,
            (self.image.height() - height) / 2,
            width,
            height,
        )
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self.opacity)
        painter.drawImage(QRectF(self.rect()), self.image, source)
        painter.setOpacity(self.opacity * (1 - self.brightness))
        painter.fillRect(self.rect(), QColor("black"))


def app_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor("#78a9ff"))
    painter = QPainter(pixmap)
    painter.setPen(QColor("#101824"))
    painter.setFont(QFont("Segoe UI", 27, QFont.Weight.Bold))
    painter.drawText(
        pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(datetime.now(get_localzone()).day)
    )
    painter.end()
    return QIcon(pixmap)


class TaskThread(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, task, parent):
        super().__init__(parent)
        self.task = task

    def run(self):
        try:
            self.succeeded.emit(self.task())
        except (LoginRequired, OAuthConfigurationError) as error:
            self.failed.emit(str(error))
        except Exception as error:  # noqa: BLE001 -- worker boundary; redact third-party exception data
            # Never log exception text/tracebacks: HTTP errors can contain private data.
            logger.warning("Background operation failed: %s", type(error).__name__)
            self.failed.emit(
                "연결 또는 저장에 실패했습니다. 기존 캐시를 표시합니다. 설정과 네트워크를 확인하세요."
            )


class MainWindow(QWidget):
    def __init__(self, settings, repository, auth, *, auto_sync=True):
        super().__init__()
        self.settings, self.repository, self.auth = settings, repository, auth
        self.config = settings.load()
        self.sync_service = SyncService(repository)
        self.zone = get_localzone()
        self.month = datetime.now(self.zone).date().replace(day=1)
        self.last_date = datetime.now(self.zone).date()
        self.worker = None
        self.pending_sync = False
        self.quitting = False
        self.last_sync = ""
        self.events = []
        self.background_image = QImage()
        self.lower_timer = QTimer(self)
        self.lower_timer.setSingleShot(True)
        self.lower_timer.setInterval(250)
        self.lower_timer.timeout.connect(self.lower_if_idle)
        self.setWindowTitle("Desktop Calendar")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setMinimumSize(350, 420)
        self.setWindowIcon(app_icon())
        self.background_canvas = BackgroundCanvas(self)
        self.background_canvas.lower()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        header = QHBoxLayout()
        brand = QLabel("DESKTOP / CALENDAR")
        brand.setObjectName("brand")
        brand.installEventFilter(self)
        header.addWidget(brand, 1)
        self.refresh_button = self.button("↻", "새로고침", self.refresh)
        self.settings_button = self.button("⚙", "설정", self.open_settings)
        header.addWidget(self.refresh_button)
        header.addWidget(self.settings_button)
        layout.addLayout(header)
        navigation = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("monthTitle")
        self.title.installEventFilter(self)
        navigation.addWidget(self.title, 1)
        navigation.addWidget(self.button("오늘", "이번 달", self.today))
        navigation.addWidget(self.button("‹", "이전 달", lambda: self.change_month(-1)))
        navigation.addWidget(self.button("›", "다음 달", lambda: self.change_month(1)))
        layout.addLayout(navigation)
        self.calendar = CalendarWidget()
        self.calendar.day_selected.connect(self.show_day)
        layout.addWidget(self.calendar, 1)
        self.status = QLabel("설정에서 Google 계정을 연결하세요.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        footer = QHBoxLayout()
        hint = QLabel("상단을 끌어 이동 · 테두리를 끌어 크기 조절")
        hint.setObjectName("muted")
        footer.addWidget(hint, 1)
        footer.addSpacing(20)
        layout.addLayout(footer)
        self.resize_handles = ResizeHandles(self)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_geometry)
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.refresh)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.tick)
        self.clock_timer.start(30000)
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.tray.setToolTip("Desktop Calendar")
        menu = QMenu(self)
        menu.addAction("달력 표시", self.reveal)
        menu.addAction("새로고침", self.refresh)
        menu.addAction("설정", self.open_settings)
        menu.addSeparator()
        menu.addAction("종료", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        self.restore_geometry()
        self.apply_appearance()
        self.render()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.screenAdded.connect(lambda screen: self.restore_geometry())
            app.screenRemoved.connect(lambda screen: self.restore_geometry())
        if auto_sync:
            self.sync_timer.start(self.config["sync_minutes"] * 60000)
            QTimer.singleShot(100, self.refresh)

    def button(self, text, tooltip, callback):
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(callback)
        return button

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
            and self.windowHandle()
        ):
            self.windowHandle().startSystemMove()
            return True
        return super().eventFilter(watched, event)

    def apply_appearance(self):
        dark = self.config["theme"] == "dark"
        bg = "#151c27" if dark else "#f7f8fc"
        custom = self.config["background"]
        if custom and QColor(custom).isValid():
            bg = QColor(custom).name()
        self.background_color = QColor(bg)
        self.background_image = QImage()
        if self.config["background_image"]:
            try:
                self.background_image = read_background(Path(self.config["background_image"]))
            except (OSError, ValueError):
                self.status.setText("배경 이미지를 읽지 못해 기본 배경을 표시합니다.")
        fg, muted, cell, border = (
            ("#e6edf7", "#8e9eb4", "#1c2634", "#293648")
            if dark
            else ("#17243a", "#65758b", "#ffffff", "#e0e5ed")
        )
        if not self.background_image.isNull():
            cell = "rgba(28, 38, 52, 150)" if dark else "rgba(255, 255, 255, 165)"
        self.setStyleSheet(f"""
            QWidget {{ background: transparent; color: {fg}; font-family: 'Segoe UI', '맑은 고딕'; font-size: {self.config["font_size"]}pt; }}
            QDialog, QMenu, QScrollArea, QComboBox, QAbstractSpinBox, QListWidget {{ background: {bg}; }}
            QLabel {{ background: transparent; }}
            QLabel#brand {{ color: {muted}; font-size: 9pt; font-weight: 600; }}
            QLabel#monthTitle {{ font-size: 25pt; font-weight: 600; padding: 12px 0; }}
            QLabel#muted, QLabel#weekday {{ color: {muted}; font-size: 8pt; }}
            QLabel#weekday {{ padding: 8px 0; }}
            QFrame#dayCell {{ background: {cell}; border: 1px solid {border}; border-radius: 5px; }}
            QFrame#dayCell[outside='true'] {{ background: transparent; }}
            QLabel#today {{ color: #78a9ff; font-weight: bold; }}
            QPushButton {{ border: 1px solid {border}; border-radius: 5px; padding: 5px 9px; }}
            QPushButton:hover {{ background: {border}; }}
            QPushButton:disabled {{ color: {muted}; }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QListWidget {{ border: 1px solid {border}; padding: 4px; }}
        """)
        self.setWindowOpacity(self.config["window"]["opacity"])
        self.background_canvas.color = self.background_color
        self.background_canvas.image = self.background_image
        self.background_canvas.opacity = self.config["image_opacity"]
        self.background_canvas.brightness = self.config["image_brightness"]
        self.background_canvas.setGeometry(self.rect())
        self.background_canvas.lower()
        self.background_canvas.update()

    def selected_calendars(self):
        calendars = self.config["calendars"]
        ids = self.config["calendar_ids"]
        return calendars if ids is None else [c for c in calendars if c["id"] in ids]

    def range_days(self):
        return visible_dates(self.month, self.config["first_weekday"])

    def render(self):
        self.title.setText(f"{self.month.year}.{self.month.month:02d}")
        key = self.sync_service.key(
            self.range_days(), [c["id"] for c in self.selected_calendars()], str(self.zone)
        )
        try:
            self.events, self.last_sync = self.repository.load(key)
        except (sqlite3.Error, ValueError, TypeError, KeyError) as error:
            logger.warning("Cache read failed: %s", type(error).__name__)
            self.events, self.last_sync = [], ""
            self.status.setText("캐시를 읽을 수 없습니다. 새로고침을 시도하세요.")
        self.calendar.render(self.month, self.events, self.config, self.zone)

    def cache_status(self, prefix=""):
        stamp = (
            datetime.fromisoformat(self.last_sync).astimezone().strftime("%m/%d %H:%M")
            if self.last_sync
            else "없음"
        )
        self.status.setText(f"{prefix}마지막 동기화: {stamp}")

    def change_month(self, delta):
        index = self.month.year * 12 + self.month.month - 1 + delta
        self.month = date(index // 12, index % 12 + 1, 1)
        self.render()
        self.cache_status()
        self.refresh()

    def today(self):
        self.month = datetime.now(self.zone).date().replace(day=1)
        self.render()
        self.refresh()

    def tick(self):
        if datetime.now(self.zone).date() != self.last_date:
            self.last_date = datetime.now(self.zone).date()
            self.render()
        self.lower_if_idle()

    def lower_if_idle(self):
        # Recheck at execution time: focus may have moved to our own dialog/menu.
        if (
            self.quitting
            or not self.isVisible()
            or self.isActiveWindow()
            or self.property("resizing")
        ):
            return
        if QApplication.activePopupWidget() or QApplication.activeModalWidget():
            return
        if any(child.isWindow() and child.isVisible() for child in self.findChildren(QWidget)):
            return
        lower_window(int(self.winId()))

    def run_task(self, task, callback):
        if self.worker is not None:
            return False
        self.worker = TaskThread(task, self)
        self.settings_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.worker.succeeded.connect(callback)
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.task_finished)
        self.worker.start()
        return True

    def task_finished(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
        self.settings_button.setEnabled(True)
        self.refresh_button.setEnabled(True)
        if self.quitting:
            self.quit_app()
        elif self.pending_sync:
            self.pending_sync = False
            self.refresh()

    def on_error(self, message):
        self.render()
        self.cache_status(message + " · ")

    def refresh(self):
        if self.quitting:
            return
        if self.worker is not None:
            self.pending_sync = True
            return
        days = self.range_days()
        selected_ids = self.config["calendar_ids"]
        zone = self.zone

        def task():
            logger.info("Sync Start")
            provider = GoogleCalendarService(self.auth.api())
            calendars = provider.calendars()
            selected = (
                calendars
                if selected_ids is None
                else [c for c in calendars if c["id"] in selected_ids]
            )
            self.sync_service.sync(provider, days, selected, zone)
            logger.info("Sync Complete")
            return calendars

        self.status.setText("Google Calendar 동기화 중…")
        self.run_task(task, self.synced)

    def synced(self, calendars):
        self.config["calendars"] = calendars
        self.save_config()
        self.render()
        self.cache_status()

    def open_settings(self):
        if self.worker is not None:
            self.status.setText("작업이 끝난 후 설정을 열 수 있습니다.")
            return
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        old = self.config
        old_background = old["background_image"]
        new = dialog.config
        imported_background = None
        if new["background_image"] and new["background_image"] != self.config["background_image"]:
            try:
                imported_background = import_background(
                    Path(new["background_image"]), self.settings.path.parent
                )
                new["background_image"] = str(imported_background)
            except (OSError, ValueError) as error:
                self.status.setText(str(error))
                return
        if new["startup"] != self.config["startup"]:
            try:
                StartupService().set_enabled(new["startup"])
            except OSError:
                if imported_background:
                    remove_managed_background(imported_background, self.settings.path.parent)
                self.status.setText("Windows 자동 실행 설정을 저장하지 못했습니다.")
                return
        self.config = new
        if not self.save_config():
            self.config = old
            if imported_background:
                remove_managed_background(imported_background, self.settings.path.parent)
            return
        if old_background and old_background != new["background_image"]:
            remove_managed_background(Path(old_background), self.settings.path.parent)
        self.apply_appearance()
        self.sync_timer.start(self.config["sync_minutes"] * 60000)
        self.render()
        if dialog.action == "login":
            try:
                load_client_config()
            except OAuthConfigurationError as error:
                self.status.setText(str(error))
                return

            def login():
                # Forget the old identity before displaying a different account's data.
                self.auth.logout()
                self.repository.clear()
                self.auth.login()

            self.config["calendars"] = []
            self.config["calendar_ids"] = None
            self.save_config()
            self.render()
            self.status.setText("브라우저에서 Google 로그인을 완료하세요. 최대 2분 대기합니다.")
            self.run_task(login, lambda _: self.queue_refresh())
        elif dialog.action == "logout":

            def logout():
                self.auth.logout()
                self.repository.clear()

            self.run_task(logout, self.logged_out)
        else:
            self.refresh()

    def queue_refresh(self):
        self.pending_sync = True

    def logged_out(self, _):
        self.config["calendars"], self.config["calendar_ids"] = [], None
        self.save_config()
        self.render()
        self.status.setText("로그아웃했습니다. 이 PC의 자격 증명과 일정 캐시를 삭제했습니다.")

    def show_day(self, cell):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{cell.day:%Y-%m-%d} · 일정")
        dialog.resize(400, 320)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        for event in cell.events:
            text = event.label(self.zone) + (f"\n{event.location}" if event.location else "")
            item = QListWidgetItem(text)
            item.setToolTip(text)
            listing.addItem(item)
        if not cell.events:
            listing.addItem("표시할 일정이 없습니다.")
        layout.addWidget(listing)
        dialog.exec()

    def save_config(self):
        try:
            self.settings.save(self.config)
            return True
        except OSError:
            self.status.setText("설정을 저장하지 못했습니다. 저장 위치 권한을 확인하세요.")
            return False

    def save_geometry(self):
        rect = self.geometry()
        self.config["window"].update(
            x=rect.x(), y=rect.y(), width=rect.width(), height=rect.height()
        )
        self.save_config()

    def restore_geometry(self):
        screens = QApplication.screens()
        primary = QApplication.primaryScreen()
        screens.sort(key=lambda screen: screen != primary)
        bounds = [
            (
                s.availableGeometry().x(),
                s.availableGeometry().y(),
                s.availableGeometry().width(),
                s.availableGeometry().height(),
            )
            for s in screens
        ]
        if bounds:
            w = self.config["window"]
            self.setGeometry(*fit_geometry((w["x"], w["y"], w["width"], w["height"]), bounds))

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "save_timer"):
            self.save_timer.start(400)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "background_canvas"):
            self.background_canvas.setGeometry(self.rect())
            self.background_canvas.lower()
        if hasattr(self, "resize_handles"):
            self.resize_handles.update()
        if hasattr(self, "save_timer"):
            self.save_timer.start(400)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self.lower_timer.stop()
            else:
                self.lower_timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        self.lower_timer.start()

    def reveal(self):
        self.showNormal()
        # showEvent must not undo an explicit tray restore on the next event-loop turn.
        self.lower_timer.stop()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.reveal()

    def contextMenuEvent(self, event):
        self.tray.contextMenu().exec(event.globalPos())

    def closeEvent(self, event):
        if self.quitting:
            event.accept()
        else:
            event.ignore()
            self.hide()

    def quit_app(self):
        self.quitting = True
        self.sync_timer.stop()
        self.save_geometry()
        if self.worker is not None:
            self.status.setText("진행 중인 작업을 마친 후 종료합니다…")
            return
        logger.info("Application Close")
        self.tray.hide()
        QApplication.quit()
