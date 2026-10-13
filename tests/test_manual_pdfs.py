"""Los manuales PDF (Basic y Plus) deben corresponder a la versión actual de la app.

Si este test falla tras subir de versión, hay que regenerarlos:
    python scripts/manual/build_manual.py
"""
import re
from pathlib import Path

import pytest

from src.__version__ import __version__

MANUAL = Path(__file__).resolve().parents[1] / "docs" / "manual"


def _keywords(data: bytes) -> str:
    """Lee /Keywords del diccionario Info (cadena PDF con escapes octales)."""
    m = re.search(rb"/Keywords \((.*?)\)\n", data, re.S)
    assert m, "El PDF no tiene metadatos /Keywords"
    raw = re.sub(rb"\\([0-7]{3})", lambda x: bytes([int(x.group(1), 8)]), m.group(1))
    return raw.decode("latin-1")


@pytest.mark.parametrize("edition", ["Basic", "Plus"])
def test_manual_pdf_es_de_la_version_actual(edition):
    pdf = MANUAL / f"AutoPrevias-Manual-{edition}.pdf"
    assert pdf.exists(), f"Falta {pdf.name}: ejecuta scripts/manual/build_manual.py"
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF")
    assert _keywords(data) == f"AutoPrevias {__version__}; manual; {edition.lower()}", (
        f"{pdf.name} no corresponde a la versión {__version__}: regenera los manuales "
        "con scripts/manual/build_manual.py")
