@echo off
cd /d "%~dp0\..\.."
call npm.cmd run viewer:semantic-freezer
