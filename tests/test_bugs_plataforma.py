"""Fallos de Windows/macOS detectados en la revisión de código (v6.0.4)."""
import struct
import sys

import numpy as np
import soundfile as sf


def test_nombres_de_archivo_validos_en_windows():
    from src.engine.export import safe_filename, output_paths
    assert safe_filename('Vol 1: Intro?') == "Vol 1 Intro"
    assert safe_filename("a/b\\c") == "a b c"
    assert safe_filename("CON") == "CON_"
    assert safe_filename("nul.wav".split(".")[0]) == "nul_"
    assert safe_filename("fin.  ") == "fin"
    assert safe_filename("???") == "PREVIA"
    assert len(safe_filename("x" * 400)) <= 150


def test_output_paths_sanea_el_nombre_del_usuario(tmp_path):
    from src.engine.export import output_paths
    p = output_paths("/música/tema.wav", str(tmp_path), True, True, custom_name='Mi: tema/1?')
    assert p["wav"].parent == tmp_path and p["wav"].name == "Mi tema 1.wav"


def test_wav_sano_con_chunks_grandes_no_se_reescribe(tmp_path):
    """Un WAV con carátula/iXML grande después del audio no es un WAV roto: no se toca el archivo del usuario."""
    from src.engine.audio_io import repair_wav_header_if_needed
    f = tmp_path / "ok.wav"
    sf.write(str(f), np.zeros((44100, 2), dtype="float32"), 44100, subtype="PCM_24")
    raw = f.read_bytes()
    big = b"x" * 700_000
    raw += b"iXML" + struct.pack("<I", len(big)) + big
    raw = raw[:4] + struct.pack("<I", len(raw) - 8) + raw[8:]
    f.write_bytes(raw)
    antes = f.read_bytes()
    assert repair_wav_header_if_needed(str(f)) is False
    assert f.read_bytes() == antes


def test_wav_con_cabecera_truncada_si_se_repara(tmp_path):
    from src.engine.audio_io import repair_wav_header_if_needed
    f = tmp_path / "roto.wav"
    sf.write(str(f), np.random.uniform(-0.5, 0.5, (44100, 2)).astype("float32"), 44100, subtype="PCM_16")
    raw = bytearray(f.read_bytes())
    pos = raw.find(b"data")
    raw[pos + 4:pos + 8] = struct.pack("<I", 1000)           # tamaño declarado absurdamente pequeño
    f.write_bytes(bytes(raw))
    assert repair_wav_header_if_needed(str(f)) is True


def test_audio_mono_se_carga_como_estereo(tmp_path):
    from src.engine.audio_io import load_audio_file
    f = tmp_path / "mono.wav"
    sf.write(str(f), np.random.uniform(-0.5, 0.5, 44100).astype("float32"), 44100)
    y, sr = load_audio_file(str(f), sr=44100, mono=False)
    assert y.shape[0] == 2 and np.allclose(y[0], y[1])


def test_tag_de_voz_mono_suena_en_los_dos_canales(tmp_path):
    from src.engine.effects import _load_tag
    f = tmp_path / "tag.wav"
    sf.write(str(f), np.random.uniform(-0.5, 0.5, 22050).astype("float32"), 44100)
    t = _load_tag(str(f), 44100, 0.0)
    assert t.shape[0] == 2


def test_slug_de_preset_no_es_nombre_reservado_de_windows():
    from src.presets import slugify
    assert slugify("con") == "con_" and slugify("NUL") == "NUL_" and slugify("Mi preset") == "Mi preset"


def test_borrar_caratula_no_borra_otro_preset(tmp_path):
    from src.presets import _delete_cover
    (tmp_path / "foo_cover.json").write_text("{}", encoding="utf-8")
    (tmp_path / "foo_cover.jpg").write_bytes(b"x")
    _delete_cover("foo", tmp_path)
    assert (tmp_path / "foo_cover.json").exists() and not (tmp_path / "foo_cover.jpg").exists()


def test_explorer_recibe_la_ruta_entre_comillas(monkeypatch, tmp_path):
    from src import notifications
    llamadas = []
    monkeypatch.setattr(notifications.subprocess, "Popen", lambda a, *k, **kw: llamadas.append(a))
    monkeypatch.setattr(notifications.sys, "platform", "win32")
    f = tmp_path / "PREVIA - mi tema.wav"
    f.write_bytes(b"x")
    assert notifications.reveal_in_os(str(f)) is True
    assert llamadas[0] == f'explorer /select,"{f}"'


def test_escritura_de_licencia_atomica(monkeypatch, tmp_path):
    from src.licensing import license as lic
    destino = tmp_path / "license.json"
    monkeypatch.setattr(lic, "_license_file", lambda: destino)
    lic._write_local({"a": 1})
    assert destino.exists() and not (tmp_path / "license.json.tmp").exists()


def test_reverificacion_no_resucita_una_licencia_desactivada(monkeypatch, tmp_path):
    from src.licensing import license as lic
    destino = tmp_path / "license.json"
    monkeypatch.setattr(lic, "_license_file", lambda: destino)
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "dev-test")
    from src.licensing.device import get_device_id
    dev = get_device_id()
    lic.save_local("CLAVE-DE-PRUEBA", "plus")

    def _desactiva_mientras_verifica(*a, **k):
        lic.clear_local()                                   # el usuario pulsa «Desactivar» durante la espera de red
        return {"success": True, "edition": "plus"}
    monkeypatch.setattr(lic, "verify_online", _desactiva_mientras_verifica)
    assert lic.reverify_if_due(force=True) == "skipped"
    assert not destino.exists()


def test_tema_se_reinicia_con_open_en_mac(monkeypatch):
    from src import themes
    llamadas = []
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda a, *k, **kw: llamadas.append(a))
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", "/Applications/AutoPrevias.app/Contents/MacOS/AutoPrevias")
    assert themes.restart_application() is True
    assert llamadas[0] == ["open", "-n", "/Applications/AutoPrevias.app"]
