@echo off
setlocal enabledelayedexpansion

echo =========================================
echo Compilando AutoPrevias para Windows x64
echo =========================================

for /f "tokens=*" %%i in ('python -c "from src.__version__ import __version__; print(__version__)"') do set VERSION=%%i
echo Version: %VERSION%

:: 1. Asegurar iconos generados
if not exist "assets\icon.ico" (
    echo Generando iconos...
    python scripts\generate_icons.py
)

:: 2. Asegurar FFmpeg estático en ffmpeg_bin/
if not exist "ffmpeg_bin" mkdir ffmpeg_bin
if not exist "ffmpeg_bin\ffmpeg.exe" (
    echo Descargando FFmpeg estatico para Windows x64...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Tyrrrz/FFmpegBin/releases/download/9.0.2/ffmpeg-windows-x64.zip' -OutFile 'ffmpeg-win.zip'; Expand-Archive -Path 'ffmpeg-win.zip' -DestinationPath 'ffmpeg_bin' -Force; Remove-Item 'ffmpeg-win.zip'"
)

:: 3. Limpiar directorio previo
if exist "dist\AutoPrevias.dist" rd /s /q "dist\AutoPrevias.dist"
if exist "dist\main.dist" rd /s /q "dist\main.dist"

:: 4. Compilación con Nuitka
echo Ejecutando Nuitka...
python -m nuitka ^
    --standalone ^
    --company-name="Radical Records" ^
    --product-name="AutoPrevias" ^
    --file-version=%VERSION%.0 ^
    --product-version=%VERSION% ^
    --file-description="AutoPrevias - Radical Records" ^
    --copyright="Copyright (c) 2026 Radical Records. Todos los derechos reservados." ^
    --windows-icon-from-ico=assets\icon.ico ^
    --windows-console-mode=disable ^
    --enable-plugin=pyside6 ^
    --include-data-dir=assets=assets ^
    --include-data-dir=ffmpeg_bin=ffmpeg_bin ^
    --include-package=librosa \
    --include-package-data=librosa ^
    --include-package-data=pedalboard ^
    --include-package-data=_soundfile_data ^
    --output-dir=dist ^
    --output-filename=AutoPrevias.exe ^
    --assume-yes-for-downloads ^
    src\main.py

if exist "dist\main.dist" (
    move "dist\main.dist" "dist\AutoPrevias.dist"
)

:: 5. Ejecutar selftest sobre el binario compilado
echo Ejecutando --selftest sobre dist\AutoPrevias.dist\AutoPrevias.exe...
"dist\AutoPrevias.dist\AutoPrevias.exe" --selftest
if %errorlevel% neq 0 (
    echo Error en selftest compilado.
    exit /b %errorlevel%
)

:: 6. Crear instalador con Inno Setup
echo Compilando instalador Inno Setup...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=%VERSION% installer\windows\setup.iss
if %errorlevel% neq 0 (
    echo Error al crear instalador Inno Setup.
    exit /b %errorlevel%
)

echo =========================================
echo BUILD COMPLETADO: dist\AutoPrevias-%VERSION%-Windows-x64-Setup.exe
echo =========================================
