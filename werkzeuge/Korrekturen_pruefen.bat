@echo off
cd /d "%~dp0.."
if not exist werkzeuge\zu_pruefen.txt (
  echo Keine offenen Korrekturen zur manuellen Pruefung vorhanden.
  echo.
  pause
  exit /b
)
python werkzeuge\korrektur_verarbeiten.py werkzeuge\zu_pruefen.txt
del werkzeuge\zu_pruefen.txt
echo.
echo Fertig.
pause
