@echo off
REM AutoPrevias BÁSICA — Radical Records
REM Doble clic para lanzar la aplicación en edición BÁSICA (solo MP3).

setlocal
set "DIR=%~dp0"
set "VENV=%DIR%.venv\Scripts\python.exe"

if not exist "%VENV%" (
    echo ERROR: entorno virtual no encontrado en %DIR%.venv
    echo Ejecuta primero el instalador o crea el venv manualmente:
    echo   python -m venv %DIR%.venv
    echo   %DIR%.venv\Scripts\pip install -r %DIR%src\requirements.txt
    echo.
    pause
    exit /b 1
)

"%VENV%" "%DIR%src\main.py" --edition=basic %*
