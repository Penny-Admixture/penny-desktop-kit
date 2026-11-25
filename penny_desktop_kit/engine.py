"""Apply engine: wallpaper, folder icons, cursors on Windows.

Everything here validates its inputs first (files exist, roles known),
then calls one of the small _win32 helpers at the bottom. Those helpers
are the only places that touch ctypes / winreg, and they raise
WindowsOnlyError off Windows — so this module imports and validates
cleanly on the Linux VM, and the tests monkeypatch the helpers to
record calls instead of touching a real desktop.

What Build 1 does NOT do (Build 2): lock screen, desktop pets.
"""

import os
import sys

SPI_SETDESKWALLPAPER = 20
SPI_SETCURSORS = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE = 0x02

FILE_ATTRIBUTE_READONLY = 0x01
FILE_ATTRIBUTE_HIDDEN = 0x02
FILE_ATTRIBUTE_SYSTEM = 0x04

# Pack cursor role -> HKCU\\Control Panel\\Cursors value name.
ROLE_TO_REGISTRY = {
    "arrow": "Arrow",
    "help": "Help",
    "appstarting": "AppStarting",
    "wait": "Wait",
    "crosshair": "Crosshair",
    "ibeam": "IBeam",
    "nwpen": "NWPen",
    "no": "No",
    "sizens": "SizeNS",
    "sizewe": "SizeWE",
    "sizenwse": "SizeNWSE",
    "sizenesw": "SizeNESW",
    "move": "Move",
    "uparrow": "UpArrow",
    "link": "Hand",
}

# Stock Windows (Aero) cursors, for Restore defaults. %SystemRoot%
# expands under the user's Windows folder (usually C:\\Windows).
DEFAULT_CURSORS = {
    "Arrow": r"%SystemRoot%\cursors\aero_arrow.cur",
    "Help": r"%SystemRoot%\cursors\aero_helpsel.cur",
    "AppStarting": r"%SystemRoot%\cursors\aero_working.ani",
    "Wait": r"%SystemRoot%\cursors\aero_busy.ani",
    "Crosshair": r"%SystemRoot%\cursors\cross.cur",
    "IBeam": r"%SystemRoot%\cursors\aero_ibeam.cur",
    "NWPen": r"%SystemRoot%\cursors\aero_pen.cur",
    "No": r"%SystemRoot%\cursors\aero_unavail.cur",
    "SizeNS": r"%SystemRoot%\cursors\aero_ns.cur",
    "SizeWE": r"%SystemRoot%\cursors\aero_ew.cur",
    "SizeNWSE": r"%SystemRoot%\cursors\aero_nwse.cur",
    "SizeNESW": r"%SystemRoot%\cursors\aero_nesw.cur",
    "Move": r"%SystemRoot%\cursors\aero_move.cur",
    "UpArrow": r"%SystemRoot%\cursors\aero_up.cur",
    "Hand": r"%SystemRoot%\cursors\aero_link.cur",
}


class WindowsOnlyError(RuntimeError):
    """This operation changes the Windows desktop and needs Windows."""


# ---------------------------------------------------------------- public API

def set_wallpaper(path):
    """Set the desktop wallpaper to the image at path. Returns path."""
    if not os.path.isfile(path):
        raise FileNotFoundError("wallpaper not found: %s" % path)
    _spi(SPI_SETDESKWALLPAPER, 0, os.path.abspath(path),
         SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
    return os.path.abspath(path)


def apply_folder_icon(folder, ico_path):
    """Give one folder a custom icon.

    Writes desktop.ini ([.ShellClassInfo] IconResource=...) into the
    folder, marks desktop.ini hidden+system and the folder read-only
    (the combination Explorer needs to honour the icon), then pokes
    the shell to refresh. Returns the desktop.ini path.
    """
    if not os.path.isdir(folder):
        raise FileNotFoundError("folder not found: %s" % folder)
    if not os.path.isfile(ico_path):
        raise FileNotFoundError("icon not found: %s" % ico_path)
    ini_path = os.path.join(folder, "desktop.ini")
    with open(ini_path, "w", encoding="utf-8") as f:
        f.write("[.ShellClassInfo]\n")
        f.write("IconResource=%s,0\n" % os.path.abspath(ico_path))
    _set_file_attributes(ini_path,
                         FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    current = _get_file_attributes(folder)
    _set_file_attributes(folder, current | FILE_ATTRIBUTE_READONLY)
    _shell_change_notify(folder)
    return ini_path


def remove_folder_icon(folder):
    """Undo apply_folder_icon: delete desktop.ini. Returns True if one
    was there, False if the folder was never customised."""
    if not os.path.isdir(folder):
        raise FileNotFoundError("folder not found: %s" % folder)
    ini_path = os.path.join(folder, "desktop.ini")
    if not os.path.isfile(ini_path):
        return False
    os.remove(ini_path)
    _shell_change_notify(folder)
    return True


def set_cursors(cursor_map):
    """Apply cursor files: {role: path}. Roles not listed keep the
    system cursor. Returns the list of roles applied, in map order."""
    for role, path in cursor_map.items():
        if role not in ROLE_TO_REGISTRY:
            raise ValueError("unknown cursor role: %r" % role)
        if not os.path.isfile(path):
            raise FileNotFoundError("cursor %r not found: %s" % (role, path))
    values = {ROLE_TO_REGISTRY[role]: os.path.abspath(path)
              for role, path in cursor_map.items()}
    _write_cursor_registry(values)
    _spi(SPI_SETCURSORS, 0, None, SPIF_SENDCHANGE)
    return list(cursor_map)


def restore_default_cursors():
    """Put every cursor back to the stock Windows (Aero) set."""
    _write_cursor_registry(dict(DEFAULT_CURSORS))
    _spi(SPI_SETCURSORS, 0, None, SPIF_SENDCHANGE)
    return sorted(DEFAULT_CURSORS)


# ------------------------------------------------------- win32-only helpers

def _require_windows():
    if sys.platform != "win32":
        raise WindowsOnlyError(
            "this changes the Windows desktop; it needs Windows (got %s)"
            % sys.platform)


def _spi(action, param, value, flags):
    """SystemParametersInfoW. Raises OSError if Windows says no."""
    _require_windows()
    import ctypes
    ok = ctypes.windll.user32.SystemParametersInfoW(action, param, value, flags)
    if not ok:
        raise OSError("SystemParametersInfoW(%d) failed" % action)


def _get_file_attributes(path):
    _require_windows()
    import ctypes
    attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
    if attrs == 0xFFFFFFFF:
        raise OSError("GetFileAttributesW failed for %s" % path)
    return attrs


def _set_file_attributes(path, attrs):
    _require_windows()
    import ctypes
    ok = ctypes.windll.kernel32.SetFileAttributesW(path, attrs)
    if not ok:
        raise OSError("SetFileAttributesW failed for %s" % path)


def _shell_change_notify(path):
    _require_windows()
    import ctypes
    SHCNE_UPDATEITEM = 0x00002000
    SHCNF_PATHW = 0x0005
    ctypes.windll.shell32.SHChangeNotify(SHCNE_UPDATEITEM, SHCNF_PATHW, path, None)


def _write_cursor_registry(values):
    """Write {value name: .cur/.ani path} under HKCU\\Control Panel\\Cursors."""
    _require_windows()
    import winreg
    key_path = r"Control Panel\Cursors"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                        winreg.KEY_SET_VALUE) as key:
        for name, path in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, path)
