import sys
import winreg
from pathlib import Path

from desktop_calendar.infrastructure.windows_api import startup_command


class StartupService:
    KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    NAME = "DesktopCalendar"

    def set_enabled(self, enabled: bool):
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.KEY) as key:
            if enabled:
                executable = Path(sys.executable)
                frozen = getattr(sys, "frozen", False)
                if not frozen:
                    executable = executable.with_name("pythonw.exe")
                winreg.SetValueEx(
                    key,
                    self.NAME,
                    0,
                    winreg.REG_SZ,
                    startup_command(str(executable), module=not frozen),
                )
            else:
                try:
                    winreg.DeleteValue(key, self.NAME)
                except FileNotFoundError:
                    pass
