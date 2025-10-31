# compile.py
import sys
import PyInstaller.__main__

# Paths to include manually
datas = [
    "main.py;.",          # main script
    "main.ui;.",          # main UI
    "replace.ui;.",       # replace dialog UI
    "settings.ui;.",      # settings dialog UI
    "themes/;themes"      # include all theme QSS files
]

# Hidden imports for PySide6 and qt_themes
hiddenimports = [
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "PySide6.QtCore",
    "PySide6.QtUiTools",
    "qt_themes",
]

# PyInstaller options
opts = [
    "main.py",
    "--name=NotepadApp",
    "--onefile",          # single executable
    "--windowed",         # no console
]

# add data files
for d in datas:
    opts.append(f"--add-data={d}")

# add hidden imports
for h in hiddenimports:
    opts.append(f"--hidden-import={h}")

# run PyInstaller
PyInstaller.__main__.run(opts)
