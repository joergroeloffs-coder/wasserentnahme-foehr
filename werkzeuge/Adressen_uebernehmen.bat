@echo off
cd /d "%~dp0.."
echo Uebernimmt geprueft Adressvorschlaege in die Karten-Datei ...
echo.
python werkzeuge\adressen_uebernehmen.py
echo.
pause
