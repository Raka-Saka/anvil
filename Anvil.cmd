@echo off
rem Launch Anvil without a console window
cd /d "%~dp0"
start "" "C:\Python312\pythonw.exe" anvil.py
