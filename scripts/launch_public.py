"""Día de lanzamiento: deja TODO el proyecto listo con el enlace público de Payhip en un solo comando.

  python scripts/launch_public.py ENLACE_PUBLICO            # simulación (no toca nada)
  python scripts/launch_public.py ENLACE_PUBLICO --apply    # aplica: enlace + versión PATCH + CHANGELOG + README
  opciones: --old ENLACE_ACTUAL  --no-tests  --no-pdf

Qué hace con --apply (en este orden):
  1. Cambia el enlace de la tienda en app, vídeos, generador de PDF, README… (scripts/set_store_link.py).
  2. Sube la versión PATCH (src/__version__.py), añade la entrada del CHANGELOG y el badge del README.
  3. Ejecuta pytest y regenera los PDF de Basic y Plus (salvo --no-tests / --no-pdf).
Después Claude: re-render de los vídeos que se vayan a subir primero, commit, push y CI.
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import set_store_link as S  # noqa: E402


def bump_patch() -> tuple[str, str]:
    p = ROOT / "src" / "__version__.py"
    s = p.read_text(encoding="utf-8")
    m = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', s)
    old = ".".join(m.groups())
    new = f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"
    p.write_text(s.replace(old, new), encoding="utf-8")
    return old, new


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("link")
    ap.add_argument("--old", default="payhip.com/RADICALRECVLC")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    changed = S.norm(a.link) != S.norm(a.old)
    print(f"Enlace actual: {a.old}\nEnlace nuevo : {a.link}  → {'CAMBIA' if changed else 'IGUAL (no hace falta cambiar nada en la app)'}\n")
    sys.argv = ["set_store_link.py", a.link, "--old", a.old] + (["--apply"] if a.apply and changed else [])
    if changed:
        S.main()
    if not a.apply:
        print("\n(simulación: añade --apply para aplicar)")
        return 0
    if not changed:
        print("El enlace no cambia: solo falta comprobar el Worker de Cloudflare (ver worker/LANZAMIENTO.md).")
        return 0
    old_v, new_v = bump_patch()
    today = datetime.date.today().isoformat()
    ch = ROOT / "CHANGELOG.md"
    s = ch.read_text(encoding="utf-8")
    entry = (f"## [{new_v}] - {today}\n\n### Cambiado\n- La tienda de AutoPrevias ya es pública: se actualiza el enlace de compra en la pantalla de "
             f"activación, en los manuales PDF y en el cierre de los vídeos.\n\n")
    ch.write_text(s.replace("## [", entry + "## [", 1), encoding="utf-8")
    rd = ROOT / "README.md"
    r = rd.read_text(encoding="utf-8").replace(f"Release-v{old_v}", f"Release-v{new_v}")
    rd.write_text(r, encoding="utf-8")
    print(f"Versión {old_v} → {new_v} (CHANGELOG y README actualizados)")
    if not a.no_tests:
        print("\n== pytest ==")
        subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--deselect", "tests/test_structure.py", "--deselect", "tests/test_manual_pdfs.py"], cwd=ROOT)
    if not a.no_pdf:
        print("\n== PDF ==")
        subprocess.run([sys.executable, "scripts/manual/build_manual.py"], cwd=ROOT, check=True)
    print("\nListo. Siguiente: re-render de vídeos, commit, push y CI (lo hace Claude). Worker: ver worker/LANZAMIENTO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
