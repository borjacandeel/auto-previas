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


def test_reverify_servicio_no_disponible_no_revoca(monkeypatch):
    # El Worker responde "unavailable" cuando Payhip falla: la licencia buena nunca se marca como revocada
    L.save_local(KEY, "plus")
    _fake_request(monkeypatch, {"success": False, "code": "unavailable"})
    assert L.reverify_if_due(force=True) == "network"
    assert "revoked" not in L.load_local() and L.check_license()[0] == L.LicenseStatus.VALID
    assert L.activate(KEY)[2] == L.MSG_UNAVAILABLE


def test_marca_de_revocada_se_limpia_al_verificar_bien(monkeypatch):
    L.save_local(KEY, "plus")
    d = L.load_local(); d["revoked"] = "invalid"; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.REVOKED
    _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    assert L.reverify_if_due(force=True) == "ok"
    assert L.check_license()[0] == L.LicenseStatus.VALID


def test_worker_distingue_caida_de_payhip_de_clave_invalida():
    js = (Path(__file__).resolve().parents[1] / "worker" / "autoprevias-license.js").read_text(encoding="utf-8")
    assert 'fail("unavailable"' in js and "unavailable" in js.split("async function payhipEdition")[1].split("export default")[0]


def test_clave_de_otra_edicion_se_rechaza(monkeypatch):
    # app Plus + clave Basic y app Basic + clave Plus: nunca se guarda ni se activa
    for app_ed, key_ed, msg in (("plus", "basic", L.MSG_KEY_BASIC_IN_PLUS), ("basic", "plus", L.MSG_KEY_PLUS_IN_BASIC)):
        monkeypatch.setattr(L, "_app_edition", lambda e=app_ed: e)
        L.clear_local()
        enviados = _fake_request(monkeypatch, {"success": True, "edition": key_ed})   # Worker antiguo: acepta
        ok, ed, err = L.activate(KEY)
        assert not ok and err == msg and L.load_local() is None
        assert enviados[0]["app_edition"] == app_ed and enviados[-1]["action"] == "deactivate"   # libera la clave
        _fake_request(monkeypatch, {"success": False, "code": "wrong_edition", "edition": key_ed})   # Worker nuevo
        assert L.activate(KEY)[2] == msg
    monkeypatch.setattr(L, "_app_edition", lambda: "plus")
    _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    assert L.activate(KEY)[:2] == (True, "plus")                      # misma edición: sí


def test_reverify_con_otra_edicion_revoca(monkeypatch):
    L.save_local(KEY, "plus")
    monkeypatch.setattr(L, "_app_edition", lambda: "plus")
    _fake_request(monkeypatch, {"success": True, "edition": "basic"})
    assert L.reverify_if_due(force=True) == "revoked"


def test_worker_comprueba_la_edicion_de_la_app():
    js = (Path(__file__).resolve().parents[1] / "worker" / "autoprevias-license.js").read_text(encoding="utf-8")
    assert "wrong_edition" in js and "app_edition" in js


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


def test_licencia_caducada_se_verifica_sola_sin_pedir_la_clave(monkeypatch):
    import src.main as M
    L.save_local(KEY, "plus")
    d = L.load_local(); d["verified_at"] = d["last_check"] = int(time.time()) - 20 * 86400; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.EXPIRED
    enviados = _fake_request(monkeypatch, {"success": True, "edition": "plus"})
    assert M._reverify_expired_blocking(None) == L.LicenseStatus.VALID
    assert enviados[0]["license_key"] == KEY and enviados[0]["action"] == "verify"


def test_licencia_caducada_con_negativa_del_servidor_queda_revocada(monkeypatch):
    import src.main as M
    L.save_local(KEY, "plus")
    d = L.load_local(); d["verified_at"] = d["last_check"] = int(time.time()) - 20 * 86400; L._write_local(d)
    _fake_request(monkeypatch, {"success": False, "code": "in_use"})
    assert M._reverify_expired_blocking(None) == L.LicenseStatus.REVOKED
    assert L.revoked_reason() == "in_use"


def test_licencia_antigua_caducada_pide_la_clave_una_vez(monkeypatch):
    import src.main as M
    L._write_local({"key_hash": "x", "edition": "basic", "verified_at": 1, "last_check": 1})
    assert M._reverify_expired_blocking(None) == L.LicenseStatus.EXPIRED


def test_vigilancia_cierra_la_app_si_el_servidor_revoca(monkeypatch):
    _qapp()
    from types import SimpleNamespace
    from PySide6.QtWidgets import QApplication, QMessageBox
    from src.ui.app import MainWindow
    cerrada, avisos = [], []
    monkeypatch.setattr(QApplication, "quit", staticmethod(lambda: cerrada.append(1)))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: avisos.append(a[2])))
    parado = []
    falso = SimpleNamespace(_export_worker=None, _license_timer=SimpleNamespace(stop=lambda: parado.append(1)))
    MainWindow._check_license_watch(falso)                      # sin revocación: no hace nada
    assert not cerrada
    L.save_local(KEY, "plus"); d = L.load_local(); d["revoked"] = "in_use"; L._write_local(d)
    MainWindow._check_license_watch(falso)
    assert cerrada and parado and "otro equipo" in avisos[0]
    # una exportación en curso no se corta
    cerrada.clear()
    corriendo = SimpleNamespace(_export_worker=SimpleNamespace(isRunning=lambda: True), _license_timer=falso._license_timer)
    MainWindow._check_license_watch(corriendo)
    assert not cerrada
