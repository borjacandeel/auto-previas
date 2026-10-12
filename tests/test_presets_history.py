"""Tests de los almacenes de presets (archivos JSON) e historial de previas."""
import json

import pytest

from src import history, presets


def test_slugify_seguro():
    assert presets.slugify("Radical Main") == "Radical Main"
    assert presets.slugify("Set/Verano:2026*?") == "Set_Verano_2026"
    assert presets.slugify("../../etc/passwd") == "etc_passwd"
    assert presets.slugify("   ") == "" and presets.slugify("..") == ""
    assert len(presets.slugify("x" * 200)) == 60


def test_preset_guardar_cargar_borrar(tmp_path):
    cover = tmp_path / "mi_portada.png"
    cover.write_bytes(b"\x89PNG fake")
    data = {
        "signature": {"artist": "DJ Test", "label": "Radical", "cover_path": str(cover)},
        "style": {"duration_sec": 60, "export": {"mp3": True}, "promo": {"enabled": True, "interval_sec": 25}},
    }
    base = tmp_path / "presets"
    assert presets.save_preset("Radical Main", data, base) == "Radical Main"
    assert presets.list_presets(base) == ["Radical Main"]
    got = presets.load_preset("Radical Main", base)
    assert got["style"] == data["style"]
    assert got["signature"]["artist"] == "DJ Test"
    # la carátula se copia junto al preset (portable) y se resuelve a ruta absoluta
    assert got["signature"]["cover_path"].startswith(str(base))
    assert (base / "Radical Main_cover.png").read_bytes() == b"\x89PNG fake"
    cover.unlink()                                    # borrar el original no rompe el preset
    assert presets.load_preset("Radical Main", base)["signature"]["cover_path"]
    # sobrescribir sin carátula elimina la copia antigua
    presets.save_preset("Radical Main", {"signature": {"artist": "X", "cover_path": ""}}, base)
    assert not list(base.glob("*_cover.*"))
    assert presets.delete_preset("Radical Main", base) is True
    assert presets.list_presets(base) == [] and presets.load_preset("Radical Main", base) is None
    assert presets.delete_preset("no existe", base) is False


def test_preset_nombre_invalido_y_json_corrupto(tmp_path):
    with pytest.raises(ValueError):
        presets.save_preset("  ..  ", {}, tmp_path)
    (tmp_path / "roto.json").write_text("{no es json", encoding="utf-8")
    presets.save_preset("Bueno", {"style": {}}, tmp_path)
    assert presets.list_presets(tmp_path) == ["Bueno"]       # el corrupto se ignora sin romper
    assert presets.load_preset("roto", tmp_path) is None


def test_preset_listado_ordenado_sin_distinguir_mayusculas(tmp_path):
    for n in ("zeta", "Alfa", "beta"):
        presets.save_preset(n, {"style": {}}, tmp_path)
    assert presets.list_presets(tmp_path) == ["Alfa", "beta", "zeta"]


def test_history_anade_lista_y_borra(tmp_path):
    f = tmp_path / "history.json"
    a = tmp_path / "PREVIA - uno.mp3"; a.write_bytes(b"x")
    t = tmp_path / "autoprevias_temp_1.wav"; t.write_bytes(b"x")
    id1 = history.add_entry("/musica/uno.wav", [str(a), str(t)], seed=42, bpm=128.04, key="8A", duration_sec=61.23,
                            settings={"fx": {"flanger": True}}, promo=True, path=f)
    id2 = history.add_entry("/musica/dos.wav", [str(tmp_path / "no_existe.mp3")], path=f)
    es = history.list_entries(f)
    assert [e["id"] for e in es] == [id2, id1]                # más reciente primero
    e1 = es[1]
    assert e1["files"] == [str(a)]                            # sin WAV temporales
    assert e1["exists"] and e1["bpm"] == 128.0 and e1["duration_sec"] == 61.2 and e1["promo"]
    assert e1["settings"] == {"fx": {"flanger": True}} and e1["title"] == "uno"
    assert es[0]["exists"] is False and es[0]["source_exists"] is False
    assert history.remove_entry(id1, f) and not history.remove_entry(id1, f)
    history.clear(f)
    assert history.list_entries(f) == []


def test_history_tolerante_a_archivo_corrupto_y_limite(tmp_path):
    f = tmp_path / "history.json"
    f.write_text("{{{", encoding="utf-8")
    assert history.list_entries(f) == []
    for i in range(history.MAX_ENTRIES + 5):
        history.add_entry(f"/x/{i}.wav", [], path=f)
    assert len(json.loads(f.read_text(encoding="utf-8"))) == history.MAX_ENTRIES
