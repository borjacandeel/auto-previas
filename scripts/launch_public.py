"""Día de lanzamiento: deja TODO el proyecto listo con los enlaces públicos de Payhip en un solo comando.

Enlaces (los que se pasen; los que no, se quedan como están):
  --basic URL   producto «AutoPrevias Basic»  (pantalla de activación de Basic, cierre del vídeo de Basic, manual Basic)
  --plus  URL   producto «AutoPrevias Plus»   (ídem para Plus, y el «pasar a Plus» del manual Basic)
  --store URL   tienda general de Radical Records (vídeos generales, README, soporte)

  python scripts/launch_public.py --basic URL --plus URL            # simulación (no toca nada)
  python scripts/launch_public.py --basic URL --plus URL --apply    # aplica
  opciones: --no-tests  --no-pdf

Con --apply: 1) reescribe src/links.py (y, si cambia la tienda, el resto de textos fijos), 2) sube la versión PATCH,
añade la entrada del CHANGELOG y el badge del README, 3) pytest y PDF de Basic y Plus.
Después Claude re-renderiza los vídeos, hace commit/push y lanza el CI.
"""
import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
import set_store_link as S  # noqa: E402

LINKS = ROOT / "src" / "links.py"


def full(u: str) -> str:
    u = u.strip().rstrip("/")
    return u if re.match(r"^https?://", u) else "https://" + u


def current() -> dict:
    s = LINKS.read_text(encoding="utf-8")
    return {k: re.search(rf'^{k}_URL = "([^"]+)"', s, re.M).group(1) for k in ("STORE", "BASIC", "PLUS")}


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
    ap.add_argument("--basic")
    ap.add_argument("--plus")
    ap.add_argument("--store")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()
    cur = current()
    new = dict(cur)
    for k, v in (("BASIC", a.basic), ("PLUS", a.plus), ("STORE", a.store)):
        if v:
            new[k] = full(v)
    todo = {k: (cur[k], new[k]) for k in cur if cur[k] != new[k]}
    print("Enlaces:")
    for k in ("STORE", "BASIC", "PLUS"):
        print(f"  {k:5s} {cur[k]}  →  {new[k]}  {'(CAMBIA)' if k in todo else '(igual)'}")
    if not todo:
        print("\nNada que cambiar en la app. Solo queda revisar el Worker de Cloudflare (worker/LANZAMIENTO.md).")
        return 0
    # 1) src/links.py
    if a.apply:
        t = LINKS.read_text(encoding="utf-8")
        for k, (_, nv) in todo.items():
            t = re.sub(rf'^({k}_URL = )"[^"]+"', rf'\1"{nv}"', t, flags=re.M)
        LINKS.write_text(t, encoding="utf-8")
        print("\nsrc/links.py actualizado.")
    # 2) textos fijos de la tienda general (promo, README, plan, CLAUDE…)
    if "STORE" in todo:
        sys.argv = ["set_store_link.py", todo["STORE"][1], "--old", todo["STORE"][0]] + (["--apply"] if a.apply else [])
        S.main()
    if not a.apply:
        print("\n(simulación: añade --apply para aplicar)")
        return 0
    old_v, new_v = bump_patch()
    today = datetime.date.today().isoformat()
    ch = ROOT / "CHANGELOG.md"
    s = ch.read_text(encoding="utf-8")
    entry = (f"## [{new_v}] - {today}\n\n### Cambiado\n- La tienda de AutoPrevias ya es pública: se actualizan los enlaces de compra de Basic y de Plus "
             f"en la pantalla de activación, en los manuales PDF y en el cierre de los vídeos.\n\n")
    ch.write_text(s.replace("## [", entry + "## [", 1), encoding="utf-8")
    rd = ROOT / "README.md"
    rd.write_text(rd.read_text(encoding="utf-8").replace(f"Release-v{old_v}", f"Release-v{new_v}"), encoding="utf-8")
    print(f"Versión {old_v} → {new_v} (CHANGELOG y README actualizados)")
    if not a.no_tests:
        print("\n== pytest ==")
        subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "--deselect", "tests/test_structure.py", "--deselect", "tests/test_manual_pdfs.py"], cwd=ROOT)
    if not a.no_pdf:
        print("\n== PDF ==")
        subprocess.run([sys.executable, "scripts/manual/build_manual.py"], cwd=ROOT, check=True)
    print("\nListo. Siguiente (Claude): re-render de vídeos, commit, push y CI. Worker: worker/LANZAMIENTO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
