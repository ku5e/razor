#!/bin/bash
echo "Razor — Mac build"

pip3 install pyinstaller pillow
pip3 install -r requirements.txt

python3 generate_icon.py
pyinstaller razor.spec --clean --noconfirm

echo ""
echo "Build complete: dist/Razor.app"
