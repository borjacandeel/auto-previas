"""Ensambla index.html a partir de index.src.html + main.js + choreo.json + rects.json + componente motion-blur."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = (HERE / "src" / "index.src.html").read_text(encoding="utf-8")
choreo = (HERE / "choreo.json").read_text()
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
