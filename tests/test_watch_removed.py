"""«Vigilar carpeta» se retiró en la 6.0.2: ya no hay código que lea carpetas solo y los ajustes viejos se descartan."""
import json

import src.config as C


def test_los_ajustes_viejos_de_vigilar_carpeta_se_descartan_al_cargar(tmp_path, monkeypatch):
    f = tmp_path / "autoprevias_config.json"
    f.write_text(json.dumps({"watch_folder_enabled": True, "watch_folder_path": "C:/Temas", "language": "es"}), encoding="utf-8")
    monkeypatch.setattr(C, "get_config_path", lambda: f)
    cfg = C.load()
    assert "watch_folder_enabled" not in cfg and "watch_folder_path" not in cfg
    assert cfg["language"] == "es"
    assert "watch_folder_enabled" not in C._DEFAULTS and "watch_folder_path" not in C._DEFAULTS


def test_la_ventana_principal_ya_no_tiene_carpeta_vigilada():
    from src.ui.app import MainWindow
    for name in ("_scan_watch_folder", "_toggle_watch_folder", "_update_watch_button_style", "_refresh_tools_menu"):
        assert not hasattr(MainWindow, name), name


def test_el_menu_herramientas_no_ofrece_vigilar_carpeta(qapp_offscreen=None):
    import inspect
    from src.ui import app
    src = inspect.getsource(app)
    assert "Vigilar carpeta" not in src and "_act_watch" not in src
