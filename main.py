import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMessageBox, QPlainTextEdit, QWidget,
    QVBoxLayout, QTabWidget, QTabBar, QInputDialog, QDialog, QComboBox,
    QDialogButtonBox, QMenu, QLabel, QLineEdit, QHBoxLayout, QPushButton, QStatusBar
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, Qt, QSize, QEvent
from PySide6.QtGui import QMouseEvent, QTextCursor, QIcon, QFont, QAction
import qt_themes  # pip install qt-themes

SETTINGS_FILE = "settings.json"
THEMES_FOLDER = "themes"  # folder containing extra .qss files

def resource_path(relative_path):
    """Get absolute path for PyInstaller bundled files."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# ---------- TabBar / TabWidget ----------
class ModernTabBar(QTabBar):
    def tabSizeHint(self, index):
        s = super().tabSizeHint(index)
        if self.tabData(index) == "plus":
            return QSize(38, s.height())
        return s

    def mouseReleaseEvent(self, event: QMouseEvent):
        # For PySide6 QMouseEvent.position() is a QPointF; convert to QPoint
        idx = self.tabAt(event.position().toPoint())
        if idx == self.count() - 1:
            # plus tab
            if hasattr(self.parent_widget, "insert_new_tab"):
                self.parent_widget.insert_new_tab()
            return
        if event.button() == Qt.MiddleButton:
            if hasattr(self.parent_widget, "close_tab"):
                self.parent_widget.close_tab(idx)
            return
        super().mouseReleaseEvent(event)

class ModernTabWidget(QTabWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setTabBar(ModernTabBar())
        self.tabBar().parent_widget = self
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.setCornerWidget(QWidget(), Qt.BottomRightCorner)
        self.add_plus_tab()
        self.currentChanged.connect(self.on_tab_changed)

    def add_plus_tab(self):
        plus = QWidget()
        self.addTab(plus, "")
        icon = QIcon.fromTheme("list-add")
        self.setTabIcon(self.count() - 1, icon)
        self.tabBar().setTabText(self.count() - 1, "")
        self.tabBar().setTabData(self.count() - 1, "plus")
        self.tabBar().setTabButton(self.count() - 1, QTabBar.RightSide, None)

    def insert_new_tab(self, text="", title="Untitled"):
        cont = QWidget()
        layout = QVBoxLayout(cont)
        layout.setContentsMargins(2, 2, 2, 2)
        editor = QPlainTextEdit()
        editor.setPlainText(str(text))
        editor.setFont(QFont("Consolas", 11))
        editor.installEventFilter(self.app)
        editor.cursorPositionChanged.connect(lambda: self.app.update_status(editor))
        layout.addWidget(editor)
        cont.setLayout(layout)
        cont.setProperty("filepath", None)
        idx = self.count() - 1
        self.insertTab(idx, cont, title)
        self.setCurrentIndex(idx)
        self.app.update_status(editor)
        self.app.update_window_title(idx)

    def close_tab(self, index):
        if index == self.count() - 1:
            return
        editor = self.get_editor(index)
        if editor and editor.document().isModified():
            choice = QMessageBox.question(
                self.app.window, "Unsaved Changes",
                "Save changes before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if choice == QMessageBox.Yes:
                self.app.save_file(index)
            elif choice == QMessageBox.Cancel:
                return
        self.removeTab(index)
        self.app.update_status()
        self.app.update_window_title()

    def get_editor(self, index=None):
        if index is None:
            index = self.currentIndex()
        w = self.widget(index)
        if w:
            return w.findChild(QPlainTextEdit)
        return None

    def on_tab_changed(self, index):
        ed = self.get_editor(index)
        self.app.update_status(ed)
        self.app.update_window_title(index)

# ---------- Dialog helpers with .ui fallback ----------
class DialogLoader:
    """Small helper: tries to load a .ui; falls back to programmatic dialog."""
    def __init__(self, parent, loader: QUiLoader):
        self.parent = parent
        self.loader = loader

    def load_settings_dialog(self, current_theme):
        ui_path = resource_path("settings.ui")
        if os.path.exists(ui_path):
            f = QFile(ui_path)
            if f.open(QFile.ReadOnly):
                dlg = self.loader.load(f, self.parent)
                f.close()
                # Expect combo named TcomboBox, but fallback to any QComboBox in dialog
                combo = dlg.findChild(QComboBox, "TcomboBox") or dlg.findChild(QComboBox)
                return dlg, combo

        # Fallback: build a simple dialog
        dlg = QDialog(self.parent)
        dlg.setWindowTitle("Themes")
        combo = QComboBox(dlg)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)
        h = QHBoxLayout()
        h.addWidget(QLabel("Themes"))
        h.addWidget(combo)
        v = QVBoxLayout(dlg)
        v.addLayout(h)
        v.addWidget(box)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        return dlg, combo

    def load_replace_dialog(self):
        ui_path = resource_path("replace.ui")
        if os.path.exists(ui_path):
            f = QFile(ui_path)
            if f.open(QFile.ReadOnly):
                dlg = self.loader.load(f, self.parent)
                f.close()
                find_edit = dlg.findChild(QLineEdit, "ReplacelineEdit")
                with_edit = dlg.findChild(QLineEdit, "WithlineEdit")
                return dlg, find_edit, with_edit

        # Fallback replace dialog
        dlg = QDialog(self.parent)
        dlg.setWindowTitle("Replace")
        find_edit = QLineEdit()
        with_edit = QLineEdit()
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form = QHBoxLayout()
        form.addWidget(QLabel("Find:"))
        form.addWidget(find_edit)
        form.addWidget(QLabel("With:"))
        form.addWidget(with_edit)
        v = QVBoxLayout(dlg)
        v.addLayout(form)
        v.addWidget(box)
        box.accepted.connect(dlg.accept)
        box.rejected.connect(dlg.reject)
        return dlg, find_edit, with_edit

# ---------- Main application ----------
class NotepadApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.loader = QUiLoader()
        self.dialogs = DialogLoader(None, self.loader)  # parent set later
        self.current_theme = "atom_one"
        self.load_settings()
        # Try to apply theme early (will fallback internally)
        self.apply_theme(self.current_theme)

        # Load main UI; if missing, create a minimal layout programmatically
        ui_file_path = resource_path("main.ui")
        if os.path.exists(ui_file_path):
            ui_file = QFile(ui_file_path)
            if not ui_file.open(QFile.ReadOnly):
                raise RuntimeError("Unable to open main.ui (file exists but cannot open)")
            self.window = self.loader.load(ui_file)
            ui_file.close()
        else:
            # Minimal main window fallback
            from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMenuBar
            mw = QMainWindow()
            central = QWidget()
            mw.setCentralWidget(central)
            layout = QVBoxLayout(central)
            tabWidget = QTabWidget()
            tabWidget.setObjectName("tabWidget")
            layout.addWidget(tabWidget)
            mw.setMenuBar(QMenuBar())
            mw.setStatusBar(QStatusBar())
            mw.resize(900, 600)
            self.window = mw

        # set dialog parent now
        self.dialogs.parent = self.window

        # replace the existing tabWidget with our ModernTabWidget
        old_tab = self.window.findChild(QTabWidget, "tabWidget")
        self.tab_widget = ModernTabWidget(self)
        if old_tab is not None:
            layout = old_tab.parentWidget().layout()
            layout.replaceWidget(old_tab, self.tab_widget)
            old_tab.setParent(None)
        else:
            # attach into main layout if no named widget existed
            central = getattr(self.window, "centralWidget", None)
            if central:
                central.layout().addWidget(self.tab_widget)

        # statusbar reference (fallback)
        self.statusbar = getattr(self.window, "statusbar", None) or self.window.findChild(QStatusBar) or self.window.statusBar()
        if self.statusbar is None:
            # create a status bar if not present
            self.statusbar = QStatusBar()
            try:
                self.window.setStatusBar(self.statusbar)
            except Exception:
                pass

        self.connect_actions()
        self.tab_widget.insert_new_tab()
        self.window.setWindowTitle("Untitled - Notepad")
        self.window.show()

    # --- settings persistence ---
    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    self.current_theme = data.get("theme", "atom_one")
        except Exception:
            self.current_theme = "atom_one"

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
                json.dump({"theme": self.current_theme}, fh, indent=2)
        except Exception:
            pass

    def apply_theme(self, theme_name):
        # clear previous stylesheet first
        self.setStyleSheet("")  # important: reset any custom QSS

        # try local .qss first
        qss_file = resource_path(os.path.join(THEMES_FOLDER, theme_name))
        if os.path.isfile(qss_file):
            try:
                with open(qss_file, "r", encoding="utf-8") as fh:
                    self.setStyleSheet(fh.read())
                    return
            except Exception:
                pass

        # fallback to qt_themes
        try:
            qt_themes.set_theme(theme_name)
        except Exception:
            pass

    # --- connect actions ---
    def connect_actions(self):
        w = self.window

        def a(name):
            return w.findChild(QAction, name)

        # File
        if a("actionNew"): a("actionNew").triggered.connect(lambda: self.tab_widget.insert_new_tab())
        if a("actionOpen"): a("actionOpen").triggered.connect(self.open_file)
        if a("actionSave"): a("actionSave").triggered.connect(lambda: self.save_file())
        if a("actionSave_As"): a("actionSave_As").triggered.connect(lambda: self.save_file_as())
        if a("actionSave_All"): a("actionSave_All").triggered.connect(self.save_all)
        if a("actionExit"): a("actionExit").triggered.connect(self.exit_app)

        # Edit
        if a("actionFind"): a("actionFind").triggered.connect(self.find_text)
        if a("actionFind_Next"): a("actionFind_Next").triggered.connect(self.find_next)
        if a("actionReplace"): a("actionReplace").triggered.connect(self.replace_text)

        # Zoom
        if a("actionZoom_In"): a("actionZoom_In").triggered.connect(lambda: self.zoom_in_current())
        if a("actionZoom_Out"): a("actionZoom_Out").triggered.connect(lambda: self.zoom_out_current())

        # Settings: inject if not present
        settings_action = w.findChild(QAction, "actionSettings")
        menu_settings = w.findChild(QMenu, "menuSettings")
        if settings_action is None:
            settings_action = QAction("Themes", self.window)
            settings_action.setObjectName("actionSettings")
            settings_action.triggered.connect(self.open_settings)
            if menu_settings:
                menu_settings.addAction(settings_action)
            else:
                # append to menubar if no menu
                try:
                    w.menuBar().addAction(settings_action)
                except Exception:
                    pass
        else:
            settings_action.triggered.connect(self.open_settings)

    # --- open settings ---
    def open_settings(self):
        dlg, combo = self.dialogs.load_settings_dialog(self.current_theme)
        # prepare theme list
        themes = []
        try:
            themes = list(qt_themes.list_themes())
        except Exception:
            themes = []
        # ensure some defaults exist
        for d in ("one_dark_two", "monokai", "nord", "catppuccin_latte", "catppuccin_frappe", "catppuccin_macchiato", "catppuccin_mocha", "atom_one", "github_dark", "github_light", "dracula"):
            if d not in themes:
                themes.append(d)
        if os.path.isdir(THEMES_FOLDER):
            for f in sorted(os.listdir(THEMES_FOLDER)):
                if f.lower().endswith(".qss") and f not in themes:
                    themes.append(f)
        if combo:
            combo.clear()
            combo.addItems(themes)
            idx = combo.findText(self.current_theme)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        res = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
        if res == QDialog.Accepted and combo:
            chosen = combo.currentText()
            if chosen:
                self.current_theme = chosen
                self.apply_theme(chosen)
                self.save_settings()
                self.show_status(f"Theme changed to {chosen}")

    # --- replace ---
    def replace_text(self):
        dlg, find_edit, with_edit = self.dialogs.load_replace_dialog()
        res = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
        if res == QDialog.Accepted:
            a = find_edit.text() if find_edit else ""
            b = with_edit.text() if with_edit else ""
            editor = self.tab_widget.get_editor()
            if editor:
                content = editor.toPlainText().replace(a, b)
                editor.setPlainText(content)
                self.show_status(f"Replaced '{a}' with '{b}'")

    # --- open / save ---
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self.window, "Open File", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception as e:
            QMessageBox.warning(self.window, "Open failed", str(e))
            return

        replaced = False
        for i in range(self.tab_widget.count() - 1):
            w = self.tab_widget.widget(i)
            title = self.tab_widget.tabText(i)
            ed = self.tab_widget.get_editor(i)
            if title == "Untitled" and ed and ed.toPlainText() == "":
                ed.setPlainText(content)
                w.setProperty("filepath", path)
                self.tab_widget.setTabText(i, os.path.basename(path))
                self.tab_widget.setCurrentIndex(i)
                replaced = True
                break
        if not replaced:
            self.tab_widget.insert_new_tab(content, os.path.basename(path))
            idx = self.tab_widget.currentIndex()
            self.tab_widget.widget(idx).setProperty("filepath", path)
        self.update_window_title()

    def save_file(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()
        w = self.tab_widget.widget(index)
        if w is None:
            return
        ed = self.tab_widget.get_editor(index)
        path = w.property("filepath")
        if not path:
            return self.save_file_as(index)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(ed.toPlainText())
            # mark saved
            ed.document().setModified(False)
            self.show_status(f"Saved {os.path.basename(path)}")
            self.update_window_title(index)
        except Exception as e:
            QMessageBox.warning(self.window, "Save failed", str(e))

    def save_file_as(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()
        w = self.tab_widget.widget(index)
        if w is None:
            return
        ed = self.tab_widget.get_editor(index)
        path, _ = QFileDialog.getSaveFileName(self.window, "Save As", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(ed.toPlainText())
            w.setProperty("filepath", path)
            self.tab_widget.setTabText(index, os.path.basename(path))
            ed.document().setModified(False)
            self.show_status(f"Saved as {os.path.basename(path)}")
            self.update_window_title(index)
        except Exception as e:
            QMessageBox.warning(self.window, "Save failed", str(e))

    def save_all(self):
        # iterate through all tabs except plus-tab
        for i in range(self.tab_widget.count() - 1):
            self.save_file(i)

    # --- find / find next ---
    def find_text(self):
        ed = self.tab_widget.get_editor()
        if not ed:
            return
        text, ok = QInputDialog.getText(self.window, "Find", "Text to find:")
        if not ok or not text:
            return
        cursor = ed.textCursor()
        cursor.movePosition(QTextCursor.Start)
        ed.setTextCursor(cursor)
        if not ed.find(text):
            cursor.movePosition(QTextCursor.Start)
            ed.setTextCursor(cursor)
            if not ed.find(text):
                QMessageBox.information(self.window, "Find", f"'{text}' not found.")

    def find_next(self):
        ed = self.tab_widget.get_editor()
        if not ed:
            return
        text, ok = QInputDialog.getText(self.window, "Find Next", "Text to find (Enter):")
        if not ok or not text:
            return
        if not ed.find(text):
            cursor = ed.textCursor()
            cursor.movePosition(QTextCursor.Start)
            ed.setTextCursor(cursor)
            if not ed.find(text):
                QMessageBox.information(self.window, "Find Next", f"'{text}' not found.")

    # --- status / title ---
    def update_status(self, editor=None):
        editor = editor or self.tab_widget.get_editor()
        if editor:
            c = editor.textCursor()
            line = c.blockNumber() + 1
            col = c.columnNumber() + 1
            chars = len(editor.toPlainText())
            self.statusbar.showMessage(f"Ln {line}, Col {col}, Ch {chars}")
        else:
            self.statusbar.showMessage("Ln 1, Col 1, Ch 0")

    def show_status(self, message, timeout=5000):
        try:
            self.statusbar.showMessage(message, timeout)
        except Exception:
            pass

    def update_window_title(self, index=None):
        if index is None:
            index = self.tab_widget.currentIndex()
        w = self.tab_widget.widget(index)
        if w is None:
            self.window.setWindowTitle("Notepad")
            return
        path = w.property("filepath")
        if path:
            name = os.path.basename(path)
        else:
            name = self.tab_widget.tabText(index)
        self.window.setWindowTitle(f"{name} - Notepad")

    # --- zooming (fixed zoom out) ---
    def zoom_in_current(self, step=1):
        ed = self.tab_widget.get_editor()
        if not ed:
            return
        f = ed.font()
        size = max(6, f.pointSize() + step)
        f.setPointSize(size)
        ed.setFont(f)

    def zoom_out_current(self, step=1):
        ed = self.tab_widget.get_editor()
        if not ed:
            return
        f = ed.font()
        size = max(6, f.pointSize() - step)
        f.setPointSize(size)   # <-- fixed: previously point size was computed but not applied
        ed.setFont(f)

    def eventFilter(self, source, event):
        if isinstance(source, QPlainTextEdit) and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_in_current()
                else:
                    self.zoom_out_current()
                return True
        return super().eventFilter(source, event)

    # --- exit ---
    def exit_app(self):
        unsaved = False
        for i in range(self.tab_widget.count() - 1):
            ed = self.tab_widget.get_editor(i)
            if ed and ed.document().isModified():
                unsaved = True
                break
        if unsaved:
            c = QMessageBox.question(self.window, "Exit", "You have unsaved changes. Exit anyway?",
                                     QMessageBox.Yes | QMessageBox.No)
            if c == QMessageBox.No:
                return
        self.quit()

# ---------- run ----------
if __name__ == "__main__":
    app = NotepadApp(sys.argv)
    sys.exit(app.exec())
