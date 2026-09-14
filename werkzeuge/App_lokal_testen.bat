@echo off
cd /d "%~dp0.."
echo Starte lokalen Server ...
start "Lokaler Server - zum Beenden schliessen" /min python -m http.server 8000
timeout /t 1 /nobreak >nul
start http://localhost:8000/index.html
echo.
echo Server laeuft im Fenster "Lokaler Server" im Hintergrund.
echo Andere Versionen im Browser aufrufen:
echo   Nutzerversion:      http://localhost:8000/nutzer/index.html
echo   Admin-Version:      http://localhost:8000/nutzer-admin/index.html
echo.
echo Zum Beenden: das Fenster "Lokaler Server" schliessen.
pause
