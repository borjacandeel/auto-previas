"""Ensambla index.html a partir de index.src.html + main.js + choreo.json + rects.json + componente motion-blur."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE / "src" / "index.src.html").read_text(encoding="utf-8")
choreo = (HERE / "choreo.json").read_text()
C = json.loads(choreo)
BEAT = 60.0 / C["bpm"]


def M(t):
    """Tiempo original -> tiempo final (suma las pausas de lectura anteriores). Igual que en main.js y build_audio.py."""
    return t + sum(b * BEAT for p, b in C["holds"] if p <= t + 1e-9)


T = C["scenes"]
ORDER = [("hook", "pain"), ("pain", "reveal"), ("reveal", "demo"), ("demo", "neon"), ("neon", "stat"), ("stat", "cta"), ("cta", None)]
for a, b in ORDER:
    end = M(C["duration"]) if b is None else M(T[b])
    src = src.replace("/*S:%s*/" % a, "%.3f" % M(T[a])).replace("/*D:%s*/" % a, "%.3f" % (end - M(T[a])))
src = src.replace("/*DUR*/", "%.3f" % M(C["duration"]))
rects = (HERE / "rects.json").read_text()
main = (HERE / "src" / "main.js").read_text(encoding="utf-8")
mb = (HERE / "compositions" / "components" / "motion-blur.html").read_text(encoding="utf-8")
i = mb.index("<script>"); j = mb.index("</script>", i) + len("</script>")
html = (src.replace("/*CHOREO*/", "window.CHOREO = " + choreo + ";")
           .replace("/*RECTS*/", "window.RECTS = " + rects + ";")
           .replace("/*MAIN*/", main)
           .replace("<!--MOTION_BLUR_SCRIPT-->", mb[i:j]))
(HERE / "index.html").write_text(html, encoding="utf-8")
print("index.html", len(html) // 1024, "KB")
