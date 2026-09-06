@echo off
cd /d "%~dp0\..\..\.."
powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Milliseconds 900; Start-Process 'http://127.0.0.1:5197/'"
npm.cmd run prop-factory:studio
