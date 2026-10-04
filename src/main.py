#!/usr/bin/env python3
"""AutoPrevias — Radical Records. Punto de entrada principal."""

import sys
import os
import tempfile
import traceback
from pathlib import Path

# Asegurar raíz en sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if not hasattr(sys, "frozen"):
    setattr(sys, "frozen", True)

from src.compat import apply_librosa_patches
apply_librosa_patches()

from src.__version__ import __version__


def run_selftest() -> int:
    """
    Ejecuta el auto-test de diagnóstico del motor completo de AutoPrevias.
    Valida importación de dependencias, backend de audio, detección musical,
    procesamiento de señal y exportación a WAV y MP3.
    Retorna 0 si todo es correcto, o 1 en caso de fallo.
    """
    print("=" * 60)
    print(f"AutoPrevias v{__version__} — MODO SELFTEST DE DIAGNÓSTICO")
    print(f"Plataforma: {sys.platform} | Python: {sys.version.split()[0]}")
    print("=" * 60)

    try:
        # 1. Comprobar imports clave
        print("[1/5] Verificando dependencias críticas...")
        import numpy as np
        import scipy
        import soundfile as sf
        import pedalboard
        import librosa
        from PySide6 import QtCore, QtWidgets, QtGui
        from src.config import get_ffmpeg_path, get_assets_dir, get_cache_dir, load as load_cfg
        from src.analysis.bpm import detect_beat_grid
        from src.analysis.structure import analyze_structure
        from src.analysis.segments import build_preview_plan
        from src.engine.export import build_preview_audio, export_files

        ffmpeg_bin = get_ffmpeg_path()
        assets_dir = get_assets_dir()
        cache_dir = get_cache_dir()

        print(f"  ✓ NumPy: {np.__version__}")
        print(f"  ✓ SciPy: {scipy.__version__}")
        print(f"  ✓ SoundFile: {sf.__version__}")
        print(f"  ✓ Pedalboard: {pedalboard.__version__}")
        librosa_ver = getattr(librosa, "__version__", None)
        if not librosa_ver:
            try:
                import librosa.version
                librosa_ver = librosa.version.version
            except Exception:
                librosa_ver = "0.11.0"
        print(f"  ✓ Librosa: {librosa_ver}")
        print(f"  ✓ Qt: {QtCore.qVersion()} (PySide6)")
        print(f"  ✓ FFmpeg binario: {ffmpeg_bin or 'No detectado (se usará fallback interno)'}")
        print(f"  ✓ Directorio assets: {assets_dir}")
        print(f"  ✓ Directorio caché: {cache_dir}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 2. Generar audio sintético
            print("\n[2/5] Generando señal sintética de prueba (15s @ 44.1kHz, 128 BPM)...")
            sr = 44100
            duration = 15.0
            n_samples = int(sr * duration)
            t = np.linspace(0, duration, n_samples, endpoint=False)

            y = 0.3 * np.sin(2 * np.pi * 440 * t)
            beat_interval = int(sr * (60.0 / 128.0))
            for b in range(0, n_samples, beat_interval):
                end_b = min(b + int(sr * 0.08), n_samples)
                t_k = np.linspace(0, 0.08, end_b - b)
                y[b:end_b] += 0.5 * np.sin(2 * np.pi * 80 * t_k) * np.exp(-t_k * 40)

            y = np.clip(y, -1.0, 1.0).astype(np.float32)
            stereo = np.stack([y, y])
            synth_src_wav = tmp_path / "selftest_source.wav"
            sf.write(str(synth_src_wav), stereo.T, sr, subtype="PCM_16")
            print(f"  ✓ Archivo fuente sintético: {synth_src_wav.name} ({duration:.1f}s)")

            # 3. Análisis rítmico y estructural
            print("\n[3/5] Analizando BPM, beat grid y estructura musical...")
            grid = detect_beat_grid(y, sr)
            print(f"  ✓ BPM detectado: {grid.bpm:.1f}")
            structure = analyze_structure(y, sr, grid)
            print(f"  ✓ Secciones detectadas: {len(structure.sections)}")

            # 4. Plan de previa y síntesis de audio
            print("\n[4/5] Generando plan de previa y procesando cortes...")
            plan = build_preview_plan(structure)
            print(f"  ✓ Segmentos en plan: {len(plan.segments)}")

            cfg = load_cfg()
            cfg["preview_min_sec"] = 5.0
            cfg["preview_max_sec"] = 15.0

            preview_audio, preview_sr, seed = build_preview_audio(
                source_path=str(synth_src_wav),
                plan=plan,
                beat_grid=grid,
                cfg=cfg,
            )
            dur_out = preview_audio.shape[1] / preview_sr
            print(f"  ✓ Audio de previa procesado: {dur_out:.2f}s ({preview_audio.shape[0]} canales @ {preview_sr} Hz)")

            # 5. Exportación a WAV y MP3
            print("\n[5/5] Verificando exportación a WAV y MP3...")
            out_stem = tmp_path / "PREVIA - Selftest_Track"
            paths = {
                "wav": out_stem.with_suffix(".wav"),
                "mp3": out_stem.with_suffix(".mp3"),
            }
            exported = export_files(preview_audio, preview_sr, paths)
            assert len(exported) >= 1, "No se generó ningún archivo en exportación"

            for fmt, p in paths.items():
                if not p.exists() or p.stat().st_size == 0:
                    raise RuntimeError(f"Fallo al exportar formato {fmt.upper()}: archivo vacío o no existe")
                print(f"  ✓ {fmt.upper()} generado: {p.name} ({p.stat().st_size} bytes)")

        print("\n" + "=" * 60)
        print("✓ SELFTEST EXITOSO: Todos los componentes funcionan correctamente.")
        print("=" * 60)
        return 0

    except Exception as e:
        print("\n" + "!" * 60)
        print(f"✗ ERROR EN SELFTEST: {e}")
        traceback.print_exc()
        print("!" * 60)
        return 1


def main():
    if "--version" in sys.argv or "-v" in sys.argv:
        print(f"AutoPrevias {__version__}")
        sys.exit(0)

    if "--selftest" in sys.argv:
        sys.exit(run_selftest())

    target = ""
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and Path(arg).is_file():
            target = arg
            break

    from src.ui.app import launch
    launch(target)


if __name__ == "__main__":
    main()
