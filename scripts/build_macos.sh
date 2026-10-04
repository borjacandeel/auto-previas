#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION=$(python3 -c "from src.__version__ import __version__; print(__version__)")
ARCH=$(uname -m)

echo "========================================="
echo "Compilando AutoPrevias v${VERSION} para macOS (${ARCH})"
echo "========================================="

# 1. Asegurar iconos generados
if [ ! -f "assets/icon.icns" ]; then
    echo "Generando assets/icon.icns..."
    .venv/bin/python3 scripts/generate_icons.py
fi

# 2. Asegurar binario estático de FFmpeg en ffmpeg_bin/
mkdir -p ffmpeg_bin
if [ ! -f "ffmpeg_bin/ffmpeg" ]; then
    echo "Descargando FFmpeg estático para macOS ${ARCH}..."
    if [ "$ARCH" = "arm64" ]; then
        curl -sL https://github.com/Tyrrrz/FFmpegBin/releases/download/9.0.2/ffmpeg-osx-arm64.zip -o /tmp/ffmpeg-macos.zip
    else
        curl -sL https://github.com/Tyrrrz/FFmpegBin/releases/download/9.0.2/ffmpeg-osx-x64.zip -o /tmp/ffmpeg-macos.zip
    fi
    unzip -q -o /tmp/ffmpeg-macos.zip -d ffmpeg_bin/
    chmod +x ffmpeg_bin/ffmpeg
    rm -f /tmp/ffmpeg-macos.zip
fi

# 3. Limpiar directorio de salida anterior
rm -rf dist/AutoPrevias.app dist/main.app dist/AutoPrevias-*.dmg

# 4. Compilación con Nuitka
echo "Ejecutando Nuitka..."
.venv/bin/nuitka \
    --standalone \
    --macos-create-app-bundle \
    --macos-app-name=AutoPrevias \
    --macos-app-icon=assets/icon.icns \
    --macos-signed-app-name=com.radicalrecords.autoprevias \
    --macos-app-version="$VERSION" \
    --company-name="Radical Records" \
    --product-name="AutoPrevias" \
    --copyright="Copyright © 2026 Radical Records. Todos los derechos reservados." \
    --enable-plugin=pyside6 \
    --include-data-dir=assets=assets \
    --include-data-dir=ffmpeg_bin=ffmpeg_bin \
    --include-package=librosa \
    --include-package-data=librosa \
    --include-package-data=pedalboard \
    --include-package-data=_soundfile_data \
    --output-dir=dist \
    --output-filename=AutoPrevias \
    --assume-yes-for-downloads \
    --disable-cache=ccache \
    src/main.py

# Si Nuitka nombró la app dist/main.app, renombrarla a dist/AutoPrevias.app
if [ -d "dist/main.app" ] && [ ! -d "dist/AutoPrevias.app" ]; then
    mv dist/main.app dist/AutoPrevias.app
fi

APP_BUNDLE="dist/AutoPrevias.app"

# 5. Firma ad-hoc (sin certificado de pago por ahora)
echo "Firmando ad-hoc el bundle..."
codesign --force --deep --sign - "$APP_BUNDLE"

# 6. Test de auto-diagnóstico sobre la aplicación compilada
echo "Ejecutando --selftest sobre el binario compilado..."
"$APP_BUNDLE/Contents/MacOS/AutoPrevias" --selftest

# 7. Crear el instalador DMG con arrastrar a Aplicaciones
DMG_NAME="AutoPrevias-${VERSION}-macOS-${ARCH}.dmg"
echo "Creando instalador $DMG_NAME..."

if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
        --volname "AutoPrevias" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "AutoPrevias.app" 175 190 \
        --hide-extension "AutoPrevias.app" \
        --app-drop-link 425 190 \
        --no-strip \
        "dist/$DMG_NAME" \
        "$APP_BUNDLE"
else
    # Fallback con hdiutil si create-dmg no estuviera
    DMG_TMP="/tmp/autoprevias_tmp.dmg"
    rm -f "$DMG_TMP" "dist/$DMG_NAME"
    hdiutil create -size 500m -fs HFS+ -volname "AutoPrevias" "$DMG_TMP"
    DEV=$(hdiutil attach -readwrite -nobrowse "$DMG_TMP" | awk 'NR==1{print $1}')
    MOUNT_DIR=$(hdiutil attach -nobrowse "$DMG_TMP" | awk 'END{print $NF}')
    cp -R "$APP_BUNDLE" "$MOUNT_DIR/"
    ln -s /Applications "$MOUNT_DIR/Applications"
    hdiutil detach "$DEV" || true
    hdiutil convert "$DMG_TMP" -format UDZO -o "dist/$DMG_NAME"
    rm -f "$DMG_TMP"
fi

echo "========================================="
echo "✓ BUILD FINALIZADO CON ÉXITO"
echo "  Bundle: $APP_BUNDLE"
echo "  Instalador: dist/$DMG_NAME ($(du -h "dist/$DMG_NAME" | cut -f1))"
echo "========================================="
