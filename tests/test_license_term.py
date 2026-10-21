"""Licencias temporales (3 / 12 meses): caducidad guardada, estado «TERM_ENDED» y reverificación."""
import time

import pytest

import src.licensing.license as L

KEY = "ABCD-1234-EFGH-5678"


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "_license_file", lambda: tmp_path / "license.json")
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "equipo-A")


def _servidor(monkeypatch, respuesta):
    monkeypatch.setattr(L, "verify_online", lambda *a, **k: dict(respuesta))


def test_licencia_permanente_no_tiene_caducidad(monkeypatch):
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": None})
    assert L.activate(KEY)[0]
    assert "expires_at" not in L.load_local()
    assert L.days_left() is None
    assert L.check_license()[0] == L.LicenseStatus.VALID


def test_licencia_temporal_vale_hasta_su_fecha(monkeypatch):
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": int(time.time()) + 90 * 86400})
    assert L.activate(KEY)[0]
    assert L.check_license()[0] == L.LicenseStatus.VALID
    assert L.days_left() == 90


def test_licencia_temporal_caduca_sin_conexion(monkeypatch):
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": int(time.time()) + 60})
    L.activate(KEY)
    d = L.load_local(); d["expires_at"] = int(time.time()) - 1; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.TERM_ENDED
    assert L.days_left() == 0


def test_servidor_dice_caducada_y_queda_marcada(monkeypatch):
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": int(time.time()) + 3600})
    L.activate(KEY)
    _servidor(monkeypatch, {"success": False, "code": "expired", "expires_at": int(time.time()) - 5})
    assert L.reverify_if_due(force=True) == "expired"
    assert L.check_license()[0] == L.LicenseStatus.TERM_ENDED


def test_comprar_otra_clave_reactiva(monkeypatch):
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": int(time.time()) + 3600})
    L.activate(KEY)
    d = L.load_local(); d["term_ended"] = True; L._write_local(d)
    assert L.check_license()[0] == L.LicenseStatus.TERM_ENDED
    _servidor(monkeypatch, {"success": True, "edition": "plus", "expires_at": int(time.time()) + 365 * 86400})
    assert L.activate("NEW1-2222-3333-4444")[0]
    assert L.check_license()[0] == L.LicenseStatus.VALID
    assert L.days_left() == 365


def test_expired_mensaje_para_el_usuario(monkeypatch):
    assert "caducado" in L.MSG_TERM_EXPIRED
