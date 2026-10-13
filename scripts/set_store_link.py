"""Cambia el enlace de la tienda de Payhip en TODO el proyecto de una vez (app, PDF, vídeos, README).

Uso:
  python scripts/set_store_link.py NUEVO_ENLACE            # simulación: solo lista lo que cambiaría
  python scripts/set_store_link.py NUEVO_ENLACE --apply    # aplica los cambios
Ejemplo: python scripts/set_store_link.py payhip.com/RadicalRecords --apply
(el enlace actual es payhip.com/RADICALRECVLC; se puede indicar otro con --old).

No toca el historial (CHANGELOG.md, progreso.md) ni los PDF/vídeos ya generados: después hay que
regenerarlos (ver los pasos que imprime el script) y publicar una versión PATCH.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "src/ui/activate.py", "src/i18n_en.py", "src/engine/video_neon.py", "scripts/manual/build_manual.py",
    "marketing/promo-video/src/index.src.html", "marketing/videos/kit/build.py", "README.md", "CLAUDE.md",
    "marketing/PLAN-VIDEOS.md",
]


def norm(s: str) -> str:
    return re.sub(r"^https?://", "", s.strip()).rstrip("/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("new")
    ap.add_argument("--old", default="payhip.com/RADICALRECVLC")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    old, new = norm(a.old), norm(a.new)
    if old == new:
        print("El enlace nuevo es igual al actual: nada que hacer.")
        return 0
    total = 0
    for rel in FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        n = s.count(old)
        if not n:
            continue
        total += n
        print(f"{'CAMBIA' if a.apply else 'cambiaría'} {n:2d} ocurrencia(s) en {rel}")
        if a.apply:
            p.write_text(s.replace(old, new), encoding="utf-8")
    print(f"\nTotal: {total} ocurrencia(s) {'cambiadas' if a.apply else '(simulación, no se ha tocado nada)'}.")
    if a.apply:
        print("""
Pasos que faltan (los hace Claude en orden):
 1. pytest + selftest, versión PATCH en src/__version__.py y CHANGELOG/README.
 2. python scripts/manual/build_manual.py  (PDF Basic y Plus con el enlace nuevo).
 3. Re-render de los vídeos de marketing: marketing/videos/kit/build.py <id> (11 vídeos) y promo-video.
 4. Commit, push y CI (workflow_dispatch con el tag nuevo).""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
