@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    start "Rewrite Studio - Frontend Server" py -m http.server 5500 --bind 127.0.0.1
    goto :launch
)

where python >nul 2>nul
if not errorlevel 1 (
    start "Rewrite Studio - Frontend Server" python -m http.server 5500 --bind 127.0.0.1
    goto :launch
)

echo Python was not found. Install Python 3 and enable the "Add Python to PATH" option, then run this file again.
pause
goto :done

:launch
timeout /t 1 /nobreak >nul
start "" "http://127.0.0.1:5500"

:done
endlocal
