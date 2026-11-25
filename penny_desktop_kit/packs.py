"""Preset pack loading and validation.

A pack is a folder under packs/ with a manifest.json:

    {
      "name": "Kawaii Pink",
      "category": "Kawaii",
      "description": "Soft pastel pink, strawberries and sparkles.",
      "wallpaper": "wallpaper.png",
      "folder_icon": "folder.ico",
      "cursors": {"arrow": "cursors/arrow.cur", "link": "cursors/link.cur"}
    }

Rules (Build 1):
  - name and category are required, non-empty strings.
  - wallpaper and folder_icon are required and must exist in the pack.
  - cursors is optional; every listed role must exist in the pack.
    Roles not listed fall back to the system cursor (see engine.py).
  - Extra keys are ignored, so packs stay forward-compatible.
  - A pack whose manifest is missing or invalid is skipped, never
    fatal: load_packs() returns (packs, errors) and the app shows
    the good packs plus a plain-language note about the bad ones.
"""

import json
import os

REQUIRED_FIELDS = ("name", "category", "wallpaper", "folder_icon")

# Cursor roles Windows actually has, for reference. Packs may list any
# subset; unlisted roles keep the system cursor.
KNOWN_CURSOR_ROLES = (
    "arrow", "help", "appstarting", "wait", "crosshair", "ibeam",
    "nwpen", "no", "sizens", "sizewe", "sizenwse", "sizenesw",
    "move", "uparrow", "link",
)


class PackError(ValueError):
    """A pack manifest is missing, malformed, or points at absent files."""


class Pack:
    """One validated theme pack."""

    def __init__(self, pack_dir, manifest):
        self.dir = pack_dir
        self.name = manifest["name"]
        self.category = manifest["category"]
        self.description = manifest.get("description", "")
        self.wallpaper = os.path.join(pack_dir, manifest["wallpaper"])
        self.folder_icon = os.path.join(pack_dir, manifest["folder_icon"])
        self.cursors = {
            role: os.path.join(pack_dir, rel)
            for role, rel in manifest.get("cursors", {}).items()
        }

    def __repr__(self):
        return "Pack(%r, category=%r)" % (self.name, self.category)


def load_pack(pack_dir):
    """Load and validate one pack directory. Raises PackError."""
    manifest_path = os.path.join(pack_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise PackError("%s: no manifest.json" % pack_dir)
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise PackError("%s: manifest.json is not valid JSON: %s" % (pack_dir, exc))
    if not isinstance(manifest, dict):
        raise PackError("%s: manifest.json must be a JSON object" % pack_dir)
    for field in REQUIRED_FIELDS:
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise PackError("%s: manifest needs a non-empty %r" % (pack_dir, field))
    for field in ("wallpaper", "folder_icon"):
        target = os.path.join(pack_dir, manifest[field])
        if not os.path.isfile(target):
            raise PackError("%s: %s file %r is missing" % (pack_dir, field, manifest[field]))
    cursors = manifest.get("cursors", {})
    if not isinstance(cursors, dict):
        raise PackError("%s: 'cursors' must be an object of role -> file" % pack_dir)
    for role, rel in cursors.items():
        if not isinstance(rel, str) or not rel.strip():
            raise PackError("%s: cursor role %r needs a file path" % (pack_dir, role))
        if not os.path.isfile(os.path.join(pack_dir, rel)):
            raise PackError("%s: cursor %r file %r is missing" % (pack_dir, role, rel))
    return Pack(pack_dir, manifest)


def load_packs(packs_dir):
    """Load every pack under packs_dir.

    Returns (packs, errors): packs is a list of Pack sorted by name,
    errors is a list of plain-language strings, one per skipped pack.
    """
    packs = []
    errors = []
    if not os.path.isdir(packs_dir):
        return packs, ["Packs folder %r not found." % packs_dir]
    for name in sorted(os.listdir(packs_dir)):
        pack_dir = os.path.join(packs_dir, name)
        if not os.path.isdir(pack_dir):
            continue
        try:
            packs.append(load_pack(pack_dir))
        except PackError as exc:
            errors.append(str(exc))
    packs.sort(key=lambda p: p.name.lower())
    return packs, errors


def categories(packs):
    """Sorted unique categories across packs, with 'All' first."""
    seen = sorted({p.category for p in packs})
    return ["All"] + seen
