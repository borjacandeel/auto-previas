"""Conexión con el servidor de licencias: plan B con los certificados de la app y motivos del fallo."""
import io
import json
import socket
import ssl
import urllib.error

import pytest

import src.licensing.license as L


class _Resp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _cert_error():
    return urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed: unable to get local issuer certificate"))


def test_los_certificados_incluidos_en_la_app_cargan():
    assert L._CA_BUNDLE.exists() and L._CA_BUNDLE.stat().st_size > 100_000
    ctx = L._make_ssl_context(bundled=True)
    assert len(ctx.get_ca_certs()) > 100
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname


def test_si_el_sistema_no_se_fia_del_certificado_reintenta_con_los_de_la_app(monkeypatch):
    contextos, llamadas = [], []
    monkeypatch.setattr(L, "_make_ssl_context", lambda bundled=False: contextos.append(bundled) or object())

    def fake_urlopen(req, timeout=0, context=None):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise _cert_error()
        return _Resp(json.dumps({"success": True, "edition": "plus"}).encode())
    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)
    data, net_error = L._request({"action": "verify"})
    assert net_error is False and data == {"success": True, "edition": "plus"}
    assert contextos == [False, True]


def test_sin_internet_no_reintenta_y_dice_el_motivo(monkeypatch):
    llamadas = []
    monkeypatch.setattr(L, "_make_ssl_context", lambda bundled=False: object())

    def fake_urlopen(req, timeout=0, context=None):
        llamadas.append(1)
        raise urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed"))
    monkeypatch.setattr(L.urllib.request, "urlopen", fake_urlopen)
    r = L.verify_online("ABCD-1234-EFGH-5678")
    assert len(llamadas) == 1
    assert r["success"] is False and r["code"] == "network" and r["error"] == L.MSG_NET_DNS


def test_si_tampoco_valen_los_certificados_de_la_app_se_avisa_de_certificados(monkeypatch):
    monkeypatch.setattr(L, "_make_ssl_context", lambda bundled=False: object())
    monkeypatch.setattr(L.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(_cert_error()))
    r = L.verify_online("ABCD-1234-EFGH-5678")
    assert r["code"] == "network" and r["error"] == L.MSG_NET_CERT


def test_otro_fallo_de_red_usa_el_mensaje_general(monkeypatch):
    monkeypatch.setattr(L, "_make_ssl_context", lambda bundled=False: object())
    monkeypatch.setattr(L.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("timed out")))
    r = L.verify_online("ABCD-1234-EFGH-5678")
    assert r["error"] == L.MSG_NETWORK


def test_el_log_de_conexion_se_escribe_en_la_carpeta_temporal_del_sistema(tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    L._ssl_log("prueba de log")
    txt = (tmp_path / "autoprevias_ssl.log").read_text(encoding="utf-8")
    assert "prueba de log" in txt


def test_los_mensajes_nuevos_tienen_traduccion_al_ingles():
    from src.i18n_en import EN
    for m in (L.MSG_NET_CERT, L.MSG_NET_DNS):
        assert m in EN
