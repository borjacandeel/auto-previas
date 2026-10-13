import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
import build
for vid in sys.argv[1:]:
    spec = build.load_spec(vid)
    print("==", vid)
    for k, sc in enumerate(spec["scenes"]):
        if sc.get("vo"):
            p, d = build.voice_line(sc["vo"], spec["voice"], spec["lang"], spec.get("speed", 1.0))
            print(f"  s{k} {sc['type']:9s} dur={sc.get('dur')} vo={d:.2f}s (+{sc.get('vo_at',0.3)}) -> {'OK' if sc.get('dur',3) >= sc.get('vo_at',0.3)+d+0.45 else 'ALARGA'}  {sc['vo'][:50]}")
