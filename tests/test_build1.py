"""Build 1 tests for penny-desktop-kit.

Run offscreen on the VM:

    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q

Covers: pack manifest load/validation, engine calls (Win32 helpers
monkeypatched — nothing here touches a real desktop), .cur build +
parse round-trip, GUI smoke test, run.bat shape (goto-style, no
parenthesised blocks). No pytest-qt: the GUI test drives QApplication
directly so the suite needs nothing beyond PySide6 + pytest.
"""

import json
import os
import struct
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from penny_desktop_kit import cursors, engine, packs
from penny_desktop_kit.version import VERSION

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS_DIR = os.path.join(ROOT, "packs")


# ------------------------------------------------------------------ version

def test_version_is_1():
    assert VERSION == 1


# --------------------------------------------------------------------- packs

def test_all_three_starter_packs_load():
    loaded, errors = packs.load_packs(PACKS_DIR)
    assert errors == []
    assert [p.name for p in loaded] == [
        "Cozy Winter", "Cyberpunk Neon", "Kawaii Pink"]
    assert {p.category for p in loaded} == {
        "Cozy Winter", "Cyberpunk", "Kawaii"}
    for p in loaded:
        assert os.path.isfile(p.wallpaper)
        assert os.path.isfile(p.folder_icon)
        assert sorted(p.cursors) == ["arrow", "link"]
        for path in p.cursors.values():
            assert os.path.isfile(path)


def test_categories_lists_all_first():
    loaded, _ = packs.load_packs(PACKS_DIR)
    assert packs.categories(loaded)[0] == "All"
    assert set(packs.categories(loaded)) == {
        "All", "Cozy Winter", "Cyberpunk", "Kawaii"}


def test_load_packs_skips_bad_pack(tmp_path):
    good = tmp_path / "good"
    good.mkdir()
    (good / "wall.png").write_bytes(b"x")
    (good / "icon.ico").write_bytes(b"x")
    (good / "manifest.json").write_text(json.dumps({
        "name": "Good", "category": "Test",
        "wallpaper": "wall.png", "folder_icon": "icon.ico"}))
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "manifest.json").write_text("{not json")
    loaded, errors = packs.load_packs(str(tmp_path))
    assert [p.name for p in loaded] == ["Good"]
    assert len(errors) == 1 and "bad" in errors[0]


def _write_pack(tmp_path, manifest, files=("wall.png", "icon.ico")):
    d = tmp_path / "p"
    d.mkdir()
    for name in files:
        (d / name).write_bytes(b"x")
    (d / "manifest.json").write_text(json.dumps(manifest))
    return str(d)


def test_pack_rejects_missing_wallpaper(tmp_path):
    d = _write_pack(tmp_path, {"name": "X", "category": "Y",
                               "wallpaper": "nope.png",
                               "folder_icon": "icon.ico"})
    with pytest.raises(packs.PackError, match="wallpaper"):
        packs.load_pack(d)


def test_pack_rejects_empty_name(tmp_path):
    d = _write_pack(tmp_path, {"name": " ", "category": "Y",
                               "wallpaper": "wall.png",
                               "folder_icon": "icon.ico"})
    with pytest.raises(packs.PackError, match="name"):
        packs.load_pack(d)


def test_pack_rejects_missing_cursor_file(tmp_path):
    d = _write_pack(tmp_path, {"name": "X", "category": "Y",
                               "wallpaper": "wall.png",
                               "folder_icon": "icon.ico",
                               "cursors": {"arrow": "gone.cur"}})
    with pytest.raises(packs.PackError, match="cursor"):
        packs.load_pack(d)


def test_pack_rejects_no_manifest(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    with pytest.raises(packs.PackError, match="manifest"):
        packs.load_pack(str(d))


# ------------------------------------------------------------------- cursors

def test_cur_round_trip(tmp_path):
    from penny_desktop_kit.cursors import build_cur, parse_cur
    im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    path = str(tmp_path / "arrow.cur")
    build_cur(im, (0, 0), path)
    info = parse_cur(path)
    assert info["type"] == 2 and info["count"] == 1
    entry = info["entries"][0]
    assert entry["width"] == 32 and entry["height"] == 32
    assert entry["hotspot"] == (0, 0)
    assert entry["offset"] == 22 and entry["bytes"] == 4264


def test_cur_hotspot_outside_rejected(tmp_path):
    with pytest.raises(ValueError, match="hotspot"):
        cursors.build_cur(Image.new("RGBA", (32, 32)), (40, 0),
                          str(tmp_path / "bad.cur"))


def test_parse_cur_rejects_garbage(tmp_path):
    bad = tmp_path / "bad.cur"
    bad.write_bytes(b"not a cursor at all, just text")
    with pytest.raises(ValueError):
        cursors.parse_cur(str(bad))


def test_shipped_cursors_parse(tmp_path):
    for cur in ("arrow.cur", "link.cur"):
        for theme in ("kawaii-pink", "cozy-winter", "cyberpunk-neon"):
            info = cursors.parse_cur(
                os.path.join(PACKS_DIR, theme, "cursors", cur))
            assert info["type"] == 2 and info["count"] == 1
    link = cursors.parse_cur(
        os.path.join(PACKS_DIR, "kawaii-pink", "cursors", "link.cur"))
    assert link["entries"][0]["hotspot"] == (15, 2)


# -------------------------------------------------------------------- engine

class _FakeWin32:
    """Records engine helper calls instead of touching Windows."""

    def __init__(self):
        self.spi_calls = []
        self.registry_writes = []
        self.attr_sets = []
        self.notifies = []

    def spi(self, action, param, value, flags):
        self.spi_calls.append((action, param, value, flags))

    def get_attrs(self, path):
        return 0

    def set_attrs(self, path, attrs):
        self.attr_sets.append((path, attrs))

    def notify(self, path):
        self.notifies.append(path)

    def write_registry(self, values):
        self.registry_writes.append(dict(values))


@pytest.fixture
def fake(monkeypatch):
    f = _FakeWin32()
    monkeypatch.setattr(engine, "_spi", f.spi)
    monkeypatch.setattr(engine, "_get_file_attributes", f.get_attrs)
    monkeypatch.setattr(engine, "_set_file_attributes", f.set_attrs)
    monkeypatch.setattr(engine, "_shell_change_notify", f.notify)
    monkeypatch.setattr(engine, "_write_cursor_registry", f.write_registry)
    return f


def test_set_wallpaper_calls_spi(tmp_path, fake):
    wall = tmp_path / "wall.png"
    wall.write_bytes(b"x")
    out = engine.set_wallpaper(str(wall))
    assert out == os.path.abspath(str(wall))
    assert fake.spi_calls == [(20, 0, os.path.abspath(str(wall)), 3)]


def test_set_wallpaper_missing_file(fake):
    with pytest.raises(FileNotFoundError):
        engine.set_wallpaper("/nope/missing.png")
    assert fake.spi_calls == []


def test_apply_folder_icon_writes_desktop_ini(tmp_path, fake):
    folder = tmp_path / "mydir"
    folder.mkdir()
    ico = tmp_path / "icon.ico"
    ico.write_bytes(b"x")
    ini = engine.apply_folder_icon(str(folder), str(ico))
    assert ini == str(folder / "desktop.ini")
    text = (folder / "desktop.ini").read_text(encoding="utf-8")
    assert "[.ShellClassInfo]" in text
    assert "IconResource=%s,0" % os.path.abspath(str(ico)) in text
    assert (str(folder / "desktop.ini"), 0x06) in fake.attr_sets
    assert (str(folder), 0x01) in fake.attr_sets
    assert fake.notifies == [str(folder)]


def test_remove_folder_icon(tmp_path, fake):
    folder = tmp_path / "mydir"
    folder.mkdir()
    assert engine.remove_folder_icon(str(folder)) is False
    (folder / "desktop.ini").write_text("x")
    assert engine.remove_folder_icon(str(folder)) is True
    assert not (folder / "desktop.ini").exists()
    assert fake.notifies == [str(folder)]


def test_set_cursors_maps_roles_and_writes_registry(tmp_path, fake):
    arrow = tmp_path / "arrow.cur"
    link = tmp_path / "link.cur"
    arrow.write_bytes(b"x")
    link.write_bytes(b"x")
    roles = engine.set_cursors({"arrow": str(arrow), "link": str(link)})
    assert roles == ["arrow", "link"]
    assert fake.registry_writes == [{
        "Arrow": os.path.abspath(str(arrow)),
        "Hand": os.path.abspath(str(link))}]
    assert fake.spi_calls == [(0x0057, 0, None, 2)]


def test_set_cursors_rejects_unknown_role(tmp_path, fake):
    cur = tmp_path / "x.cur"
    cur.write_bytes(b"x")
    with pytest.raises(ValueError, match="unknown cursor role"):
        engine.set_cursors({"wiggle": str(cur)})
    assert fake.registry_writes == [] and fake.spi_calls == []


def test_restore_default_cursors(fake):
    names = engine.restore_default_cursors()
    assert names == sorted(engine.DEFAULT_CURSORS)
    assert fake.registry_writes == [dict(engine.DEFAULT_CURSORS)]
    assert fake.spi_calls == [(0x0057, 0, None, 2)]


def test_engine_raises_windows_only_off_windows(tmp_path):
    # No monkeypatching: the real helpers must refuse on Linux.
    wall = tmp_path / "wall.png"
    wall.write_bytes(b"x")
    with pytest.raises(engine.WindowsOnlyError):
        engine.set_wallpaper(str(wall))


# ----------------------------------------------------------------- run.bat

def test_run_bat_has_no_parenthesised_blocks():
    text = open(os.path.join(ROOT, "run.bat"), encoding="utf-8").read()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("if"):
            assert "(" not in line and ")" not in line, line
    assert "git pull" in text
    assert "pyw" in text


# ----------------------------------------------------------------------- GUI

def test_gui_smoke_offscreen():
    from PySide6.QtWidgets import QApplication
    from penny_desktop_kit.ui_main import MainWindow

    app = QApplication.instance() or QApplication([])
    loaded, errors = packs.load_packs(PACKS_DIR)
    assert errors == []
    window = MainWindow(loaded, PACKS_DIR)
    try:
        window.show()
        app.processEvents()
        assert window.windowTitle() == "penny-desktop-kit — Build 1"
        assert len(window._cards) == 3
        assert window.selected is not None
        assert window.selected.name == "Cozy Winter"  # first, sorted by name
        # Category filter hides the other two cards.
        window._filter_cards("Kawaii")
        visible = [p.name for p, b in window._cards.items() if b.isVisible()]
        assert visible == ["Kawaii Pink"]
        window._filter_cards("All")
        assert all(b.isVisible() for b in window._cards.values())
        # Apply on Linux must fail gracefully in the status bar, never crash.
        window._apply_all()
        assert "needs Windows" in window.statusBar().currentMessage()
        window._restore_defaults()
        assert "needs Windows" in window.statusBar().currentMessage()
    finally:
        window.close()


def test_main_entry_stdio_guard():
    # install_null_stdio must survive a pythonw-style None stdio.
    import penny_desktop_kit_main as main_mod
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        main_mod.install_null_stdio()
        assert sys.stdout is not None and sys.stderr is not None
        sys.stdout.write("hello from nowhere\n")
        sys.stderr.write("and error\n")
    finally:
        sys.stdout, sys.stderr = old_out, old_err
