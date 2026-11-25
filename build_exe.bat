@echo off
chcp 65001 >nul
pyinstaller --noconfirm --windowed --name ShagaiNaadan --add-data "assets;assets" main.py
echo.
echo Готово: dist\ShagaiNaadan\ShagaiNaadan.exe
pause
