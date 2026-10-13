"""Licencia «un equipo por clave»: identificador de equipo, almacenamiento local, reverificación y desactivación."""
import json
import re
import subprocess
import shutil
import time
from pathlib import Path

import pytest

import src.licensing.license as L
from src.licensing import device as D

KEY = "ABCD-1234-EFGH-5678"


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "_license_file", lambda: tmp_path / "license.json")
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "equipo-A")
    yield


def _otro_equipo(monkeypatch, nombre="equipo-B"):
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", nombre)


def test_device_id_es_un_hash_estable():
    a = D.get_device_id()
    assert re.fullmatch(r"[0-9a-f]{64}", a)
    assert a == D.get_device_id()
    assert "equipo-A" not in a


def test_device_id_distinto_entre_equipos(monkeypatch):
    a = D.get_device_id()
    _otro_equipo(monkeypatch)
    assert D.get_device_id() != a


def test_clave_guardada_no_va_en_claro_y_no_se_lee_en_otro_equipo(monkeypatch, tmp_path):
    L.save_local(KEY, "plus")
    raw = (tmp_path / "license.json").read_text()
    assert KEY not in raw and KEY.replace("-", "") not in raw
    data = L.load_local()
    assert L._decode_key(data["key_enc"], D.get_device_id()) == KEY
    _otro_equipo(monkeypatch)
    assert L._decode_key(data["key_enc"], D.get_device_id()) != KEY


def test_check_license_estados(monkeypatch):
    assert L.check_license() == (L.LicenseStatus.UNLICENSED, "")
    L.save_local(KEY, "plus")
    assert L.check_license() == (L.LicenseStatus.VALID, "plus")
    # licencia copiada a otro equipo
    _otro_equipo(monkeypatch)
    assert L.check_license() == (L.LicenseStatus.UNLICENSED, "")
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "equipo-A")
    # gracia agotada
    d = L.load_local(); d["verified_at"] = int(time.time()) - 15 * 86400; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.EXPIRED
    # revocada por el servidor
    d["revoked"] = "in_use"; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.REVOKED


def test_licencia_antigua_sin_equipo_sigue_valiendo():
    L._write_local({"key_hash": "x", "edition": "basic", "verified_at": int(time.time()), "last_check": int(time.time())})
    assert L.check_license() == (L.LicenseStatus.VALID, "basic")


def _fake_request(monkeypatch, respuesta, red=False):
    enviados = []
    def fake(payload):
        enviados.append(payload)
        return (None, True) if red else (respuesta, False)
    monkeypatch.setattr(L, "_request", fake)
    return enviados


def test_activate_envia_equipo_y_guarda(monkeypatch):
    enviados = _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    ok, ed, err = L.activate("  " + KEY.lower() + " ")
    assert (ok, ed, err) == (True, "plus", "")
    p = enviados[0]
    assert p["action"] == "activate" and p["license_key"] == KEY and p["device_id"] == D.get_device_id()
    assert L.load_local()["device"] == D.get_device_id()


def test_activate_en_uso_en_otro_equipo(monkeypatch):
    _fake_request(monkeypatch, {"success": False, "code": "in_use"})
    ok, ed, err = L.activate(KEY)
    assert not ok and err == L.MSG_IN_USE and L.load_local() is None


def test_activate_sin_conexion_o_clave_mala(monkeypatch):
    _fake_request(monkeypatch, None, red=True)
    assert L.activate(KEY)[2] == L.MSG_NETWORK
    _fake_request(monkeypatch, {"success": False, "error": "Clave no válida"})   # Worker antiguo (sin code)
    assert L.activate(KEY)[2] == L.MSG_INVALID


def test_reverify_ok_renueva_la_gracia(monkeypatch):
    L.save_local(KEY, "basic")
    d = L.load_local(); d["last_check"] = d["verified_at"] = int(time.time()) - 8 * 86400; L._write_local(d)
    enviados = _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    assert L.reverify_if_due() == "ok"
    assert enviados[0]["action"] == "verify" and enviados[0]["license_key"] == KEY
    d = L.load_local()
    assert d["edition"] == "plus" and time.time() - d["verified_at"] < 5


def test_reverify_no_hace_nada_si_es_pronto(monkeypatch):
    L.save_local(KEY, "plus")
    enviados = _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    assert L.reverify_if_due() == "skipped" and enviados == []
    assert L.reverify_if_due(force=True) == "ok"


def test_reverify_revoca_si_esta_en_otro_equipo(monkeypatch):
    L.save_local(KEY, "plus")
    _fake_request(monkeypatch, {"success": False, "code": "in_use"})
    assert L.reverify_if_due(force=True) == "revoked"
    assert L.check_license()[0] == L.LicenseStatus.REVOKED


def test_reverify_sin_red_no_revoca_y_reintenta(monkeypatch):
    L.save_local(KEY, "plus")
    d = L.load_local(); antiguo = d["last_check"] = int(time.time()) - 8 * 86400; L._write_local(d)
    _fake_request(monkeypatch, None, red=True)
    assert L.reverify_if_due() == "network"
    d = L.load_local()
    assert "revoked" not in d and d["last_check"] == antiguo          # se reintentará en el próximo arranque


def test_reverify_con_licencia_antigua_no_puede():
    L._write_local({"key_hash": "x", "edition": "basic", "verified_at": 1, "last_check": 1})
    assert L.reverify_if_due() == "legacy"


def test_desactivar_libera_en_el_servidor(monkeypatch):
    L.save_local(KEY, "plus")
    enviados = _fake_request(monkeypatch, {"success": True})
    assert L.deactivate_online() == (True, "ok") and enviados[0]["action"] == "deactivate"
    _fake_request(monkeypatch, {"success": False, "code": "not_owner"})
    assert L.deactivate_online()[0] is True                           # ya no era suyo: nada que liberar
    _fake_request(monkeypatch, None, red=True)
    assert L.deactivate_online() == (False, "network")


def test_describe_license_revocada():
    from src.ui.about import describe_license
    assert describe_license({"key_hash": "abcdef12", "edition": "plus", "verified_at": time.time(), "revoked": "in_use"})["state"] == "revoked"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no disponible")
def test_worker_js():
    r = subprocess.run(["node", "--test", str(Path(__file__).resolve().parents[1] / "worker" / "test_worker.mjs")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1000:]


def _qapp():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_pantalla_de_activacion_explica_que_esta_en_otro_equipo():
    _qapp()
    from PySide6.QtWidgets import QLabel
    from src.ui.activate import ActivationDialog
    d = ActivationDialog(reason="in_use")
    textos = " ".join(l.text() for l in d.findChildren(QLabel))
    assert "otro equipo" in textos
    d2 = ActivationDialog(reason="invalid")
    assert "ya no es válida" in " ".join(l.text() for l in d2.findChildren(QLabel))


def test_desactivar_desde_la_ventana_de_licencia_libera_en_el_servidor(monkeypatch):
    _qapp()
    from src.ui.about import LicenseDialog
    llamadas = []
    monkeypatch.setattr(L, "deactivate_online", lambda: (llamadas.append(1), (True, "ok"))[1])
    dlg = LicenseDialog("9.9.9", "plus")
    assert dlg._release_on_server() is True and llamadas == [1]
