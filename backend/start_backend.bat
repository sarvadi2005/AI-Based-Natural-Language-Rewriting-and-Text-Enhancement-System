@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    goto :done
)

where python >nul 2>nul
if not errorlevel 1 (
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    goto :done
)

echo Python was not found. Install Python 3.10 or later and enable "Add Python to PATH".
pause

:done
endlocal
