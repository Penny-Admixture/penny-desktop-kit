"""Entry point for penny-desktop-kit.

Startup order:

1. Fix stdio for windowless launch: under pythonw there is no
   console, so sys.stdout/sys.stderr are None and any print() raises.
   install_null_stdio() runs FIRST, before any other import, and
   points them at log files in data/.
2. Set the Windows app identity (AppUserModelID
   PennyAdmixture.PennyDesktopKit) so the app gets its own taskbar
   item, never shared with another app.
3. Load the theme packs and launch the gallery window.

A startup failure (bad Python, missing PySide6, broken import)
never shows a console -- there is none. It is written to
data/crash.log instead, with the full traceback.
"""

import datetime
import os
import sys
import traceback

APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

MIN_PYTHON = (3, 10)


class _NullStream:
    """Last-resort stdio sink: swallows writes when even the log-file
    redirect failed. Never raises, never blocks, holds nothing."""

    def write(self, *args, **kwargs):
        return 0

    def writelines(self, lines):
        pass

    def flush(self):
        pass

    def isatty(self):
        return False


def _data_dir():
    return os.path.join(APP_DIR, "data")


def install_null_stdio(data_dir=None):
    """Under pythonw sys.stdout/sys.stderr are None and every print()
    raises. Redirect them to log files in data/ so prints land on
    disk instead. No-op when a real console exists. Never raises:
    if a log file cannot be opened, that stream falls back to a
    null sink, so a logging failure can never kill the app."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    if data_dir is None:
        data_dir = _data_dir()
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        sys.stdout = _NullStream()
        sys.stderr = _NullStream()
        return
    for name, attr in (("stdout.log", "stdout"), ("stderr.log", "stderr")):
        if getattr(sys, attr) is None:
            try:
                setattr(sys, attr, open(os.path.join(data_dir, name), "a",
                                        encoding="utf-8", errors="replace"))
            except OSError:
                setattr(sys, attr, _NullStream())


def _set_app_identity():
    """Windows taskbar identity: PennyAdmixture.PennyDesktopKit.
    No-op off Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "PennyAdmixture.PennyDesktopKit")
    except Exception:
        pass


def _crash_log(data_dir, exc):
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "crash.log"), "a",
                  encoding="utf-8", errors="replace") as f:
            f.write("[%s] FATAL startup failure:\n"
                    % datetime.datetime.now().isoformat(timespec="seconds"))
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
            f.write("\n")
    except OSError:
        pass


def main():
    install_null_stdio()
    data_dir = _data_dir()
    if sys.version_info < MIN_PYTHON:
        _crash_log(data_dir, RuntimeError(
            "penny-desktop-kit needs Python %d.%d or newer (got %s)"
            % (MIN_PYTHON + (sys.version.split()[0],))))
        return 1
    try:
        _set_app_identity()
        from PySide6.QtWidgets import QApplication
        from penny_desktop_kit.packs import load_packs
        from penny_desktop_kit.ui_main import MainWindow

        packs_dir = os.path.join(APP_DIR, "packs")
        packs, errors = load_packs(packs_dir)
        app = QApplication(sys.argv)
        icon_path = os.path.join(APP_DIR, "penny_desktop_kit", "app.ico")
        if os.path.isfile(icon_path):
            from PySide6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))
        window = MainWindow(packs, packs_dir)
        if errors:
            window.statusBar().showMessage(
                "%d themes loaded. Skipped %d broken pack(s): %s"
                % (len(packs), len(errors), "; ".join(errors)))
        window.show()
        return app.exec()
    except Exception as exc:  # noqa: BLE001 - startup must never show a console
        _crash_log(data_dir, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
