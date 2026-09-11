import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QLockFile, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from desktop_calendar.infrastructure.credential_store import CredentialStore
from desktop_calendar.repositories.event_repository import EventRepository
from desktop_calendar.services.google_auth_service import GoogleAuthService
from desktop_calendar.services.settings_service import SettingsService
from desktop_calendar.ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, help="별도 설정/캐시 경로 (테스트용)")
    parser.add_argument(
        "--smoke-test", action="store_true", help="네트워크 없이 창을 열고 자동 종료"
    )
    parser.add_argument("--screenshot", type=Path, help="smoke-test 화면 저장 경로")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("DesktopCalendar")
    app.setQuitOnLastWindowClosed(False)
    config_dir = args.data_dir or Path(os.environ["APPDATA"]) / "DesktopCalendar"
    data_dir = args.data_dir or Path(os.environ["LOCALAPPDATA"]) / "DesktopCalendar"
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(data_dir / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        QMessageBox.information(
            QWidget(), "Desktop Calendar", "이미 실행 중입니다. 시스템 트레이에서 달력을 여세요."
        )
        return 0
    logs = data_dir / "logs"
    logs.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        logs / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("desktop_calendar")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    # Third-party libraries may log OAuth redirect URLs. Disable their output.
    logging.getLogger().handlers.clear()
    logging.getLogger().addHandler(logging.NullHandler())
    logger.info("Application Start")
    try:
        window = MainWindow(
            SettingsService(config_dir / "config.json"),
            EventRepository(data_dir / "calendar.db"),
            GoogleAuthService(CredentialStore()),
            auto_sync=not args.smoke_test,
        )
    except Exception as error:  # noqa: BLE001 -- startup boundary; do not disclose credential errors
        logger.error("Initialization failed: %s", type(error).__name__)
        QMessageBox.critical(
            QWidget(),
            "Desktop Calendar",
            "초기화에 실패했습니다. 저장 경로와 Windows 자격 증명 서비스를 확인하세요.",
        )
        return 1
    window.show()
    if args.smoke_test:

        def finish():
            if args.screenshot:
                args.screenshot.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(args.screenshot))
            window.quit_app()

        QTimer.singleShot(1200, finish)
    result = app.exec()
    lock.unlock()
    return result
