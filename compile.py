import sys
import os
import PyInstaller.__main__

# Determine the proper separator for add-data
if sys.platform.startswith("win"):
    sep = ";"
else:
    sep = ":"

# Paths to include manually
datas = [
    f"main.py{sep}.",
    f"main.ui{sep}.",
    f"replace.ui{sep}.",
    f"settings.ui{sep}.",
    f"themes/{sep}themes"
]

# Hidden imports for PySide6 and qt_themes
hiddenimports = [
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "PySide6.QtCore",
    "PySide6.QtUiTools",
    "qt_themes",
]

opts = [
    "main.py",
    "--name=NotepadApp",
    "--onefile",
    "--windowed",
]

for d in datas:
    opts.append(f"--add-data={d}")

for h in hiddenimports:
    opts.append(f"--hidden-import={h}")

PyInstaller.__main__.run(opts)
