#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m PyInstaller --noconfirm --clean --windowed --onedir \
  --icon icon.icns --osx-bundle-identifier at.achtm.fotokaraoke \
  --name '8M Foto Karaoke' app.py
hdiutil create -volname '8M Foto Karaoke' -srcfolder 'dist/8M Foto Karaoke.app' \
  -ov -format UDZO 'dist/8M-Foto-Karaoke-macOS.dmg'
printf 'Fertig: dist/8M-Foto-Karaoke-macOS.dmg\n'
