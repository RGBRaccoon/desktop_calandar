# Build from the repository root: python -m PyInstaller DesktopCalendar.spec
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['run.py'], pathex=['src'],
    datas=collect_data_files('googleapiclient') + collect_data_files('tzdata'),
    hiddenimports=['keyring.backends.Windows', 'tzlocal.win32'],
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DesktopCalendar', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='DesktopCalendar')
