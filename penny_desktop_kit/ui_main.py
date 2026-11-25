"""Main window: theme gallery + one-click apply.

Layout: category list on the left, theme cards in the middle, a
preview pane with the apply buttons on the right, status bar along
the bottom. Every apply action reports plainly in the status bar —
what changed, or why it didn't.

On non-Windows (this VM) the engine raises WindowsOnlyError and the
status bar says so instead of crashing: the gallery, preview and
pack loading all still work offscreen for testing.
"""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import engine
from .packs import categories
from .version import VERSION


class MainWindow(QMainWindow):
    def __init__(self, packs, packs_dir, parent=None):
        super().__init__(parent)
        self.packs = packs
        self.packs_dir = packs_dir
        self.selected = None
        self._cards = {}

        self.setWindowTitle("penny-desktop-kit — Build %d" % VERSION)
        self.setMinimumSize(1000, 620)
        self.resize(1200, 750)

        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        # ---- left: categories
        self.category_list = QListWidget(self)
        self.category_list.addItems(categories(packs))
        self.category_list.setCurrentRow(0)
        self.category_list.setMaximumWidth(180)
        self.category_list.currentTextChanged.connect(self._filter_cards)
        layout.addWidget(self.category_list)

        # ---- middle: theme cards in a scrollable grid
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        grid_host = QWidget(scroll)
        self.grid = QVBoxLayout(grid_host)
        self.grid.setAlignment(Qt.AlignTop)
        scroll.setWidget(grid_host)
        layout.addWidget(scroll, stretch=2)

        # ---- right: preview + actions
        side = QVBoxLayout()
        self.preview = QLabel("Pick a theme to preview it.", self)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(260)
        self.preview.setStyleSheet("QLabel { background: #222; color: #ddd; }")
        side.addWidget(self.preview)
        self.theme_label = QLabel("", self)
        self.theme_label.setWordWrap(True)
        side.addWidget(self.theme_label)

        self.apply_all_btn = QPushButton("Apply whole theme", self)
        self.apply_all_btn.clicked.connect(self._apply_all)
        side.addWidget(self.apply_all_btn)
        self.apply_wall_btn = QPushButton("Apply wallpaper only", self)
        self.apply_wall_btn.clicked.connect(self._apply_wallpaper)
        side.addWidget(self.apply_wall_btn)
        self.apply_icon_btn = QPushButton("Apply folder icon only", self)
        self.apply_icon_btn.clicked.connect(self._apply_icon)
        side.addWidget(self.apply_icon_btn)
        self.apply_cursor_btn = QPushButton("Apply cursors only", self)
        self.apply_cursor_btn.clicked.connect(self._apply_cursors)
        side.addWidget(self.apply_cursor_btn)
        self.restore_btn = QPushButton("Restore defaults", self)
        self.restore_btn.clicked.connect(self._restore_defaults)
        side.addWidget(self.restore_btn)

        side.addWidget(QLabel("Folder for the custom icon:", self))
        target_row = QHBoxLayout()
        self.target_edit = QLineEdit(self)
        self.target_edit.setPlaceholderText("Pick a folder…")
        target_row.addWidget(self.target_edit)
        browse_btn = QPushButton("Browse…", self)
        browse_btn.clicked.connect(self._browse_target)
        target_row.addWidget(browse_btn)
        side.addLayout(target_row)
        side.addStretch(1)
        layout.addLayout(side, stretch=1)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(
            "%d themes loaded. Pick one, then Apply." % len(packs))
        self._build_cards()

    # ------------------------------------------------------------ gallery

    def _build_cards(self):
        for pack in self.packs:
            btn = QToolButton(self)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setText(pack.name)
            pix = QPixmap(pack.wallpaper)
            if not pix.isNull():
                btn.setIcon(pix.scaled(320, 180, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))
            btn.setIconSize(btn.icon().actualSize(btn.sizeHint()))
            btn.clicked.connect(
                lambda _checked=False, p=pack: self._select(p))
            self._cards[pack] = btn
            self.grid.addWidget(btn)
        if self.packs:
            self._select(self.packs[0])

    def _filter_cards(self, category):
        for pack, btn in self._cards.items():
            btn.setVisible(category == "All" or pack.category == category)

    def _select(self, pack):
        self.selected = pack
        pix = QPixmap(pack.wallpaper)
        if pix.isNull():
            self.preview.setText("No preview for %s." % pack.name)
            self.preview.setPixmap(QPixmap())
        else:
            self.preview.setPixmap(pix.scaled(
                self.preview.size(), Qt.KeepAspectRatio,
                Qt.SmoothTransformation))
            self.preview.setText("")
        roles = ", ".join(sorted(pack.cursors)) or "none (system cursors)"
        self.theme_label.setText(
            "%s — %s\n%s\nFolder icon: %s\nCursors: %s"
            % (pack.name, pack.category, pack.description or "No description.",
               os.path.basename(pack.folder_icon), roles))
        self.statusBar().showMessage("Selected %s." % pack.name)

    # ------------------------------------------------------------ actions

    def _need_theme(self):
        if self.selected is None:
            self.statusBar().showMessage("Pick a theme first.")
            return None
        return self.selected

    def _apply_all(self):
        pack = self._need_theme()
        if pack is None:
            return
        parts = []
        try:
            engine.set_wallpaper(pack.wallpaper)
            parts.append("wallpaper")
        except Exception as exc:
            self._fail("wallpaper", exc)
            return
        try:
            folder = self._icon_target()
            engine.apply_folder_icon(folder, pack.folder_icon)
            parts.append("folder icon on %s" % folder)
        except Exception as exc:
            self._fail("folder icon", exc)
            return
        try:
            roles = engine.set_cursors(pack.cursors)
            parts.append("cursors (%s)" % ", ".join(roles) if roles
                         else "cursors (none in this pack)")
        except Exception as exc:
            self._fail("cursors", exc)
            return
        self.statusBar().showMessage(
            "Applied %s: %s." % (pack.name, "; ".join(parts)))

    def _apply_wallpaper(self):
        pack = self._need_theme()
        if pack is None:
            return
        try:
            engine.set_wallpaper(pack.wallpaper)
        except Exception as exc:
            self._fail("wallpaper", exc)
            return
        self.statusBar().showMessage("Wallpaper set to %s." % pack.name)

    def _apply_icon(self):
        pack = self._need_theme()
        if pack is None:
            return
        try:
            folder = self._icon_target()
            engine.apply_folder_icon(folder, pack.folder_icon)
        except Exception as exc:
            self._fail("folder icon", exc)
            return
        self.statusBar().showMessage(
            "Folder icon set on %s." % folder)

    def _apply_cursors(self):
        pack = self._need_theme()
        if pack is None:
            return
        try:
            roles = engine.set_cursors(pack.cursors)
        except Exception as exc:
            self._fail("cursors", exc)
            return
        if roles:
            self.statusBar().showMessage(
                "Cursors set: %s." % ", ".join(roles))
        else:
            self.statusBar().showMessage(
                "This pack ships no cursors — system cursors kept.")

    def _restore_defaults(self):
        try:
            engine.restore_default_cursors()
        except Exception as exc:
            self._fail("restore cursors", exc)
            return
        folder = self.target_edit.text().strip()
        note = ""
        if folder and os.path.isdir(folder):
            try:
                if engine.remove_folder_icon(folder):
                    note = " Folder icon removed from %s." % folder
                else:
                    note = " No custom icon on %s." % folder
            except Exception as exc:
                self._fail("restore folder icon", exc)
                return
        self.statusBar().showMessage("Defaults restored.%s" % note)

    def _icon_target(self):
        folder = self.target_edit.text().strip()
        if not folder:
            raise FileNotFoundError(
                "pick a folder for the icon first (Browse…).")
        if not os.path.isdir(folder):
            raise FileNotFoundError("folder not found: %s" % folder)
        return folder

    def _browse_target(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Pick a folder for the custom icon")
        if folder:
            self.target_edit.setText(folder)

    def _fail(self, what, exc):
        if isinstance(exc, engine.WindowsOnlyError):
            self.statusBar().showMessage(
                "Can't apply %s here — this needs Windows." % what)
        else:
            self.statusBar().showMessage(
                "Couldn't apply %s: %s" % (what, exc))
