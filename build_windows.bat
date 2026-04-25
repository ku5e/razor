@echo off
echo Razor — Windows build

pip install pyinstaller pillow >nul 2>&1
pip install -r requirements.txt >nul 2>&1

python generate_icon.py
pyinstaller razor.spec --clean --noconfirm

echo.
echo Build complete: dist\razor\razor.exe
pause
