@echo off
cd /d "%~dp0.."
echo Hole neue Korrektur-Mails ab ...
echo.
python werkzeuge\mail_abrufen.py
echo.
pause
