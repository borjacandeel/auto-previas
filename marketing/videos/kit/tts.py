"""Narración para los vídeos. Proveedores (prefijo de la voz):
  kokoro:<voz>  Kokoro-82M local (Apache-2.0), p. ej. kokoro:ef_dora
  piper:<voz>   Piper local (voces es_ES de licencia libre), p. ej. piper:es_ES-davefx-medium
  edge:<voz>    Voces neuronales de Microsoft (castellano de España nativo), p. ej. edge:es-ES-ElviraNeural
Uso: python tts.py <proveedor:voz> <idioma> <velocidad> <salida.wav> "texto"."""
import asyncio
import ssl
import subprocess
import sys
import wave
from pathlib import Path
import soundfile as sf

CACHE = Path.home() / ".cache" / "hyperframes" / "tts"
_k = None


def synth_edge(text: str, voice: str, speed: float, out: Path):
    import edge_tts
    from edge_tts import communicate
    communicate._SSL_CTX = ssl.create_default_context(cafile="/root/.ccr/ca-bundle.crt")
    rate = f"{int(round((speed - 1.0) * 100)):+d}%"
    mp3 = out.with_suffix(".mp3")
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(mp3)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "44100", "-ac", "1", str(out)], check=True)
    mp3.unlink()


def synth_piper(text: str, voice: str, out: Path):
    from piper import PiperVoice
    v = PiperVoice.load(f"/tmp/claude-0/piper/{voice}.onnx")
    with wave.open(str(out), "wb") as w:
        v.synthesize_wav(text, w)


def synth(text: str, voice: str = "ef_dora", lang: str = "es", speed: float = 1.0):
    global _k
    from kokoro_onnx import Kokoro
    if _k is None:
        _k = Kokoro(str(CACHE / "models" / "kokoro-v1.0.onnx"), str(CACHE / "voices" / "voices-v1.0.bin"))
    samples, sr = _k.create(text, voice=voice, speed=speed, lang=lang)
    return samples, sr


if __name__ == "__main__":
    voice, lang, speed, out, text = sys.argv[1], sys.argv[2], float(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
    prov, _, name = voice.partition(":")
    if not name:
        prov, name = "kokoro", voice
    if prov == "edge":
        synth_edge(text, name, speed, out)
    elif prov == "piper":
        synth_piper(text, name, out)
    else:
        s, sr = synth(text, name, lang, speed)
        sf.write(str(out), s, sr)
    d, sr = sf.read(str(out))
    print(f"{len(d)/sr:.2f}s")
