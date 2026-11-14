@echo off
REM Double-click me. First run installs Betty (needs Python 3.10+ from python.org).
cd /d "%~dp0"
where python >nul 2>nul || (echo Python is not installed. Get it free from https://www.python.org/downloads/ then run me again. & pause & exit /b 1)
python -c "import betty" 2>nul || python -m pip install --quiet -e .
python -m betty %*
echo.
pause
