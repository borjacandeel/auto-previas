"""Enlaces de compra de AutoPrevias en Payhip (un único sitio para cambiarlos).

El día del lanzamiento `scripts/launch_public.py --basic ... --plus ...` reescribe estas tres constantes.
 · STORE_URL : tienda general de Radical Records (vídeos generales, README, soporte).
 · BASIC_URL : producto «AutoPrevias Basic».
 · PLUS_URL  : producto «AutoPrevias Plus» (licencia de 3 meses desde la v5.4).
 · *_12M_URL : productos de 12 meses (vacío = aún no creado: se enseña la tienda en su lugar).
"""
from __future__ import annotations

import re

STORE_URL = "https://payhip.com/RADICALRECVLC"
BASIC_URL = "https://payhip.com/b/NVkaK"
PLUS_URL = "https://payhip.com/b/mTjEL"
BASIC_12M_URL = ""      # PENDIENTE: enlace del producto Basic de 12 meses
PLUS_12M_URL = ""       # PENDIENTE: enlace del producto Plus de 12 meses


def short(url: str) -> str:
    """Enlace sin «https://» para mostrarlo en pantalla y en los vídeos."""
    return re.sub(r"^https?://", "", url.strip()).rstrip("/")


def url_for(edition: str) -> str:
    """Enlace de compra de la edición indicada («plus» o «basic»)."""
    return PLUS_URL if str(edition).lower() == "plus" else BASIC_URL


def renew_options(edition: str) -> list[tuple[str, str]]:
    """Opciones para comprar/renovar la licencia de la edición: [(duración, enlace)], 3 y 12 meses."""
    plus = str(edition).lower() == "plus"
    three = PLUS_URL if plus else BASIC_URL
    twelve = (PLUS_12M_URL if plus else BASIC_12M_URL) or STORE_URL
    return [("3 meses", three), ("12 meses", twelve)]
