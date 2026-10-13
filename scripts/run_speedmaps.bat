@echo off
REM Runs the speedmap generator for today's Q1 Lakeside meeting.
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python run.py --fresh %* >> output\run_log.txt 2>&1
