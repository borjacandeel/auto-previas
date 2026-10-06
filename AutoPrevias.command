#!/bin/bash
# AutoPrevias — Radical Records
# Doble clic para lanzar la aplicación.

DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$DIR/.venv/bin/python"

if [ ! -f "$VENV" ]; then
    echo "ERROR: entorno virtual no encontrado en $DIR/.venv"
    echo "Ejecuta primero el instalador o crea el venv manualmente:"
    echo "  /opt/homebrew/bin/python3.11 -m venv $DIR/.venv"
    echo "  $DIR/.venv/bin/pip install -r $DIR/src/requirements.txt"
    echo ""
    read -p "Pulsa Enter para cerrar..."
    exit 1
fi

cd "$DIR" || exit 1
"$VENV" "$DIR/src/main.py" "$@"
