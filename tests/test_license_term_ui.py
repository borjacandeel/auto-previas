"""Interfaz de las licencias temporales: menú «Licencia caducada», panel de activación y ⚙ Licencia."""
import time

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

import src.licensing.license as L
from src import links
from src.ui import about, activate

KEY = "ABCD-1234-EFGH-5678"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _aislado(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "_license_file", lambda: tmp_path / "license.json")
    monkeypatch.setenv("AUTOPREVIAS_DEVICE_ID", "equipo-A")


def _guardar(monkeypatch, expires_at, term_ended=False, edition="plus"):
    monkeypatch.setattr(L, "verify_online", lambda *a, **k: {"success": True, "edition": edition, "expires_at": expires_at})
    assert L.activate(KEY)[0]
    if term_ended:
        d = L.load_local(); d["term_ended"] = True; L._write_local(d)


def test_enlaces_de_renovacion_por_edicion():
    assert links.renew_options("plus")[0] == ("3 meses", links.PLUS_URL)
    assert links.renew_options("basic")[0] == ("3 meses", links.BASIC_URL)
    assert links.renew_options("plus")[1] == ("12 meses", links.PLUS_12M_URL or links.STORE_URL)
    assert links.renew_options("basic")[1] == ("12 meses", links.BASIC_12M_URL or links.STORE_URL)
    assert links.PLUS_12M_URL.startswith("https://payhip.com/b/") and links.BASIC_12M_URL.startswith("https://payhip.com/b/")


def test_menu_caducada_ofrece_comprar_3_y_12_meses_y_clave_nueva(app, monkeypatch):
    abiertos = []
    monkeypatch.setattr(activate.ExpiredDialog, "_open", staticmethod(lambda u: abiertos.append(u)))
    d = activate.ExpiredDialog(edition="plus", expired_on="2026-10-01")
    textos = [b.text() for b in d.findChildren(QPushButton)]
    assert any("3 meses" in t for t in textos) and any("12 meses" in t for t in textos)
    assert d._btn_enter.text() == "Ya tengo una clave nueva"
    d._buy_buttons[0].click(); d._buy_buttons[1].click()
    assert abiertos == [u for _, u in links.renew_options("plus")]
    d._btn_enter.click()
    assert d.result() == activate.ExpiredDialog.ENTER_KEY


def test_menu_caducada_salir_devuelve_rechazo(app):
    d = activate.ExpiredDialog(edition="basic")
    d._btn_quit.click()
    assert d.result() == 0


def test_flujo_caducada_activa_clave_nueva_y_vuelve_al_menu_si_se_cancela(app, monkeypatch):
    pasos = []

    class FakeMenu:
        n = 0
        ENTER_KEY = activate.ExpiredDialog.ENTER_KEY

        def __init__(self, *a, **k): pass
        def exec(self):
            FakeMenu.n += 1
            pasos.append("menu")
            return self.ENTER_KEY if FakeMenu.n <= 2 else 0

    class FakeAct:
        n = 0

        class _Sig:
            def __init__(self): self.cb = []
            def connect(self, f): self.cb.append(f)

        def __init__(self, *a, **k):
            self.activated = FakeAct._Sig()
            self.reason = k.get("reason")
        def exec(self):
            FakeAct.n += 1
            pasos.append("activar:" + str(self.reason))
            if FakeAct.n == 2:                       # la 2.ª vez el usuario sí activa
                for f in self.activated.cb: f("plus")

    monkeypatch.setattr(activate, "ExpiredDialog", FakeMenu)
    monkeypatch.setattr(activate, "ActivationDialog", FakeAct)
    assert activate.run_expired_flow(None, edition="plus") == "plus"
    assert pasos == ["menu", "activar:term_ended", "menu", "activar:term_ended"]


def test_flujo_caducada_salir_devuelve_none(app, monkeypatch):
    class Menu:
        ENTER_KEY = 1
        def __init__(self, *a, **k): pass
        def exec(self): return 0
    monkeypatch.setattr(activate, "ExpiredDialog", Menu)
    assert activate.run_expired_flow(None, edition="plus") is None


def test_panel_activacion_tras_caducar_dice_que_caduco_y_enseña_los_dos_enlaces(app):
    d = activate.ActivationDialog(reason="term_ended")
    from PySide6.QtWidgets import QLabel
    textos = " ".join(l.text() for l in d.findChildren(QLabel))
    assert "caducado" in textos and "3 meses" in textos and "12 meses" in textos


def test_describe_license_temporal():
    ahora = time.time()
    base = {"verified_at": ahora, "key_hash": "abcdef0123456789"}
    vivo = about.describe_license({**base, "expires_at": ahora + 5 * 86400 - 10}, now=ahora)
    assert vivo["state"] == "active" and vivo["term_days"] == 5 and vivo["expires"] not in ("", "—")
    muerto = about.describe_license({**base, "expires_at": ahora - 5}, now=ahora)
    assert muerto["state"] == "term_ended" and muerto["term_days"] == 0
    marcado = about.describe_license({**base, "expires_at": ahora + 86400, "term_ended": True}, now=ahora)
    assert marcado["state"] == "term_ended"
    perm = about.describe_license(base, now=ahora)
    assert perm["state"] == "active" and perm["term_days"] is None and perm["expires"] == ""


def test_dialogo_licencia_muestra_dias_y_renovar_solo_si_es_temporal(app, monkeypatch):
    import src.config as C
    monkeypatch.setattr(C, "_get_baked_edition", lambda: "plus")
    monkeypatch.setattr(about.LicenseDialog, "_refresh_term_from_server", lambda self: None)   # sin red en el test
    _guardar(monkeypatch, int(time.time()) + 3 * 86400)
    d = about.LicenseDialog("5.9.9", "plus")
    assert not d._renew_box.isHidden()
    assert "quedan 3 días" in d._lbl_detail.text()
    assert len(d._renew_btns) == 2

    L.clear_local()
    _guardar(monkeypatch, None)
    d2 = about.LicenseDialog("5.9.9", "plus")
    assert d2._renew_box.isHidden()
    assert "quedan" not in d2._lbl_detail.text()


def test_dialogo_licencia_caducada(app, monkeypatch):
    import src.config as C
    monkeypatch.setattr(C, "_get_baked_edition", lambda: "basic")
    monkeypatch.setattr(about.LicenseDialog, "_refresh_term_from_server", lambda self: None)
    _guardar(monkeypatch, int(time.time()) + 100, term_ended=True, edition="basic")
    d = about.LicenseDialog("5.9.9", "basic")
    assert "caducada" in d._lbl_state.text().lower()
    assert not d._renew_box.isHidden()
