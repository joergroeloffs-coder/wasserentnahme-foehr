@echo off
cd /d "%~dp0.."
echo Suche Adressvorschlaege fuer Stellen ohne Lage-Text ...
echo Das kann je nach Anzahl mehrere Minuten dauern (1 Anfrage pro Sekunde).
echo.
python werkzeuge\adressen_vorschlagen.py
echo.
pause
