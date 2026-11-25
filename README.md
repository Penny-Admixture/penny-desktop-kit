# penny-desktop-kit

One-click Windows desktop themes: wallpaper, folder icons and cursors,
bundled as preset packs. Free, local, no account, no subscription,
no cloud — the opposite of the $19.99/month store apps doing the same
job. Everything ships in the repo; nothing is downloaded at install
or first run.

## Run it

Double-click `launch-hidden.vbs` (zero console flash) or `run.bat`
(`git pull` first, then launches under pythonw). Needs Python 3.10+
with PySide6 on PATH. A startup failure goes to `data/crash.log`.

## Build 1 — what works

- Theme gallery: 3 starter packs (Kawaii Pink, Cozy Winter,
  Cyberpunk Neon), category filter, wallpaper preview.
- Apply whole theme, or wallpaper / folder icon / cursors separately.
- Restore defaults: stock Aero cursors back, folder icon removed.
- Folder icon target is picked with a Browse button; the icon is
  applied to that one folder (desktop.ini + .ico, Explorer refresh).

## Pack format

A pack is a folder under `packs/`:

```
packs/kawaii-pink/
  manifest.json   name, category, description, wallpaper, folder_icon, cursors
  wallpaper.png   2048x1152
  folder.ico      multi-size .ico (256 down to 16)
  cursors/
    arrow.cur     normal pointer, hotspot (0,0)
    link.cur      hand pointer, hotspot (15,2)
```

Cursor roles not listed in a pack keep the system cursor. A pack
with a bad manifest is skipped with a note in the status bar, never
fatal. Add a pack by dropping a folder in `packs/` and restarting.

## How applying works (Windows)

- Wallpaper: `SystemParametersInfoW(SPI_SETDESKWALLPAPER)` with
  update-ini + send-change.
- Folder icon: `desktop.ini` (`[.ShellClassInfo] IconResource=...`)
  written into the folder, desktop.ini hidden+system, folder
  read-only, `SHChangeNotify` to refresh Explorer.
- Cursors: `HKCU\Control Panel\Cursors` values + `SystemParametersInfoW(SPI_SETCURSORS)`.
- Restore defaults writes the stock Aero cursor paths back.

All Win32 calls live in `penny_desktop_kit/engine.py` behind small
helpers that raise `WindowsOnlyError` off Windows, so the module
imports and validates on Linux too.

## Rebuilding assets

Art sources live in the pack folders (`media-generation-*.webp` is
the generated folder art). Re-run after regenerating art:

```
python tools/build_assets.py
```

It renames wallpapers, builds `folder.ico` from the art, draws the
cursor art and writes real `.cur` files (see
`penny_desktop_kit/cursors.py` for the format).

## Tests

```
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q
```

Covers manifest load/validation, engine calls (Win32 mocked),
`.cur` file validity (built then parsed back), and a GUI smoke
test offscreen.

## Next builds (see GOALS.md)

- Build 2: lock screen + desktop pets.
- Later: more packs, pack download/sharing, per-folder icon memory.
