# Release requires an app-owner Desktop OAuth registration. Never bundle user tokens.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
sys.path.insert(0, str(root / 'src'))
from desktop_calendar.services.oauth_config import load_client_config, OAuthConfigurationError

client = root / 'src' / 'desktop_calendar' / 'resources' / 'oauth_client.json'
try:
    load_client_config(client)
except OAuthConfigurationError as error:
    raise SystemExit(str(error))

a = Analysis(
    [str(root / 'run.py')], pathex=[str(root / 'src')],
    datas=collect_data_files('googleapiclient') + collect_data_files('tzdata')
          + [(str(client), 'desktop_calendar/resources')],
    hiddenimports=['keyring.backends.Windows', 'tzlocal.win32'],
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='DesktopCalendar', console=False)
