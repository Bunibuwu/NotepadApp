# compile.py
import PyInstaller.__main__
import sys
import os

# Files/folders to include
assets = [
    ("main.ui", "."),
    ("settings.ui", "."),
    ("replace.ui", "."),
    ("themes", "themes")
]

# Platform-specific separator
sep = ";" if sys.platform.startswith("win") else ":"

# Build --add-data args
add_data_args = []
for src, dst in assets:
    if os.path.exists(src):
        add_data_args.append(f"--add-data={src}{sep}{dst}")

# Run PyInstaller
PyInstaller.__main__.run([
    "main.py",
    "--onefile",
    "--windowed",            # no console window
    "--name=NotepadApp",
    "--collect-all=PySide6",  # bundle all Qt DLLs, plugins, resources
] + add_data_args)
