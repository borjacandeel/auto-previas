"""Enlaces de compra de AutoPrevias en Payhip (un único sitio para cambiarlos).

El día del lanzamiento `scripts/launch_public.py --basic ... --plus ...` reescribe estas tres constantes.
 · STORE_URL : tienda general de Radical Records (vídeos generales, README, soporte).
 · BASIC_URL : producto «AutoPrevias Basic».
 · PLUS_URL  : producto «AutoPrevias Plus».
"""
from __future__ import annotations

import re

STORE_URL = "https://payhip.com/RADICALRECVLC"
BASIC_URL = "https://payhip.com/RADICALRECVLC"
PLUS_URL = "https://payhip.com/RADICALRECVLC"


def short(url: str) -> str:
    """Enlace sin «https://» para mostrarlo en pantalla y en los vídeos."""
    return re.sub(r"^https?://", "", url.strip()).rstrip("/")


def url_for(edition: str) -> str:
    """Enlace de compra de la edición indicada («plus» o «basic»)."""
    return PLUS_URL if str(edition).lower() == "plus" else BASIC_URL
