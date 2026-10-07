@echo off
REM AutoPrevias PLUS — Radical Records
REM Doble clic para lanzar la aplicación en edición PLUS (todas las funcionalidades).

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

"%VENV%" "%DIR%src\main.py" --edition=plus %*
