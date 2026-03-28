@echo off
title DailyNewsDrop
color 0B
cd /d "%~dp0"
echo.
echo  ╔══════════════════════════════════════╗
echo  ║      DAILYNEWSDROP (DND)             ║
echo  ╚══════════════════════════════════════╝
echo.
echo  Starting server...
start http://localhost:5055/dashboard
python app.py
pause
