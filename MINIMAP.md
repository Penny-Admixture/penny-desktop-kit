# MINIMAP — penny-desktop-kit (hand this + the relevant source files to any model)

## What it is

Windows desktop-customization app, Python + PySide6. A gallery of
theme packs (wallpaper + folder icon + cursors); one click applies a
whole theme. Free and local — no account, no subscription, no cloud.
Build 1, 2026-11-25. Penny's order, ~02:58 EST: "Yes, build a
starter version" (after Finn's difficulty answer on the Custom
Desktop Kit screenshot: shell easy, presets the real work).

## Layout

```
penny_desktop_kit_main.py   entry: null stdio for pythonw, AppUserModelID
                            PennyAdmixture.PennyDesktopKit, crash.log
penny_desktop_kit/
  __init__.py               VERSION re-export
  version.py                VERSION = 1 (plain integer builds)
  packs.py                  Pack + load_pack/load_packs, validation
  cursors.py                .cur build (ICO type 2 + hotspot) + parse
  engine.py                 set_wallpaper / apply_folder_icon /
                            remove_folder_icon / set_cursors /
                            restore_default_cursors; Win32 helpers
                            (_spi, _get/set_file_attributes,
                            _shell_change_notify, _write_cursor_registry)
  ui_main.py                MainWindow: categories, cards, preview,
                            apply buttons, folder picker, status bar
  app.ico                   app icon (kawaii folder art)
packs/<theme>/              manifest.json, wallpaper.png (2048x1152),
                            folder.ico, cursors/{arrow,link}.cur
                            + media-generation-*.webp source art
tools/build_assets.py       regenerate pack assets from generated art
tests/test_build1.py         pytest suite (see below)
run.bat                     git pull + pyw launch, goto-style, no parens
launch-hidden.vbs           zero-flash start (double-click this)
README.md / GOALS.md        developer guide / build tracker
```

## Key facts

- Pack manifest: name, category (required); wallpaper, folder_icon
  (required, must exist); cursors {role: file} optional — unlisted
  roles keep the system cursor. Bad pack = skipped with a note.
- Cursor registry: HKCU\Control Panel\Cursors; roles mapped in
  engine.ROLE_TO_REGISTRY (arrow->Arrow, link->Hand, ...).
  Restore defaults writes engine.DEFAULT_CURSORS (stock Aero paths).
- .cur format: ICO container type 2, hotspot in the directory
  entry, 32bpp BGRA DIB + 1bpp AND mask, bottom-up, 32x32.
  parse_cur() verifies type/count/hotspot/bounds.
- Engine public functions validate inputs first, then call the
  _win32 helpers; helpers raise WindowsOnlyError off Windows, so
  the module imports on the Linux VM and tests monkeypatch them.
- GUI offscreen smoke test works (QT_QPA_PLATFORM=offscreen).
  Apply buttons on Linux show "Can't apply ... — this needs
  Windows." in the status bar, never a crash.
- Folder icon needs desktop.ini hidden+system AND the folder
  read-only, then SHChangeNotify, or Explorer ignores it.
- Binaries in the tree (do NOT go through github push-files,
  which rejects non-UTF-8): 3x wallpaper.png (~8.2 MB total),
  3x folder.ico, 6x .cur, app.ico, 3x source webp. Push code +
  manifests + docs via push-files; binaries need the browser
  upload flow. Total tree ~8.8 MB.
- Lock screen + desktop pets are OUT of Build 1 (Build 2).

## Current state — Build 1 (2026-11-25)

Starter done on the VM, tests green (see test run in the report).
NOT yet live-verified on Windows: wallpaper actually changing,
folder icon appearing in Explorer, cursors actually switching —
Penny runs git pull + run.bat after the push, then reports.
