import ctypes
import subprocess
import sys
from ctypes import wintypes


def fit_geometry(rect: tuple, screens: list[tuple]) -> tuple:
    x, y, width, height = map(int, rect)
    target = next((s for s in screens if s[0] <= x < s[0] + s[2] and s[1] <= y < s[1] + s[3]), None)
    if target is None:
        target = screens[0]
        x, y = target[0] + 40, target[1] + 40
    sx, sy, sw, sh = target
    width, height = min(width, sw), min(height, sh)
    return max(sx, min(x, sx + sw - width)), max(sy, min(y, sy + sh - height)), width, height


def startup_command(executable: str, module: bool = False) -> str:
    command = subprocess.list2cmdline([executable])
    # Always quote a bare executable as well, for stable registry values.
    if not command.startswith('"'):
        command = f'"{command}"'
    return command + (" -m desktop_calendar" if module else "")


def lower_window(handle: int):
    if sys.platform != "win32":
        return
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    function = user32.SetWindowPos
    function.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    function.restype = wintypes.BOOL
    function(handle, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
