"""Narración local con Kokoro-82M (kokoro-onnx). Uso: python tts.py <voz> <idioma> <velocidad> <salida.wav> "texto"."""
import sys
from pathlib import Path
import soundfile as sf
from kokoro_onnx import Kokoro

CACHE = Path.home() / ".cache" / "hyperframes" / "tts"
_k = None


def synth(text: str, voice: str = "ef_dora", lang: str = "es", speed: float = 1.0):
    global _k
    if _k is None:
        _k = Kokoro(str(CACHE / "models" / "kokoro-v1.0.onnx"), str(CACHE / "voices" / "voices-v1.0.bin"))
    samples, sr = _k.create(text, voice=voice, speed=speed, lang=lang)
    return samples, sr


if __name__ == "__main__":
    voice, lang, speed, out, text = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5]
    s, sr = synth(text, voice, lang, speed)
    sf.write(out, s, sr)
    print(f"{len(s)/sr:.2f}s")
