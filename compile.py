# compile.py
import sys
import os
from PyInstaller.__main__ import run

# Clear previous build
for d in ("build", "dist", "NotepadApp.spec"):
    if os.path.exists(d):
        if os.path.isdir(d):
            import shutil
            shutil.rmtree(d)
        else:
            os.remove(d)

# PyInstaller arguments
opts = [
    "main.py",                # your main script
    "--name=NotepadApp",      # output executable name
    "--onefile",              # single exe
    "--windowed",             # no console window
    "--add-data=themes{}themes".format(os.pathsep),  # include themes folder
]

# Run PyInstaller
run(opts)
