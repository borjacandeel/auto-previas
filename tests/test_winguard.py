"""v6.5: arranque seguro en Windows (si la app se cierra de golpe, el siguiente arranque cambia de motor y luego modo seguro)."""
from src import winguard as W


def test_arranque_normal_usa_wmf_y_queda_pendiente(tmp_path):
    f = tmp_path / "s.json"
    env = {}
    c = W.prepare(f, env=env)
    assert env["QT_MEDIA_BACKEND"] == "windows" and c["pending"] and not c["safe_mode"]
    W.mark_ok(f)
    env = {}
    c = W.prepare(f, env=env)                        # salió bien: se repite lo mismo
    assert env["QT_MEDIA_BACKEND"] == "windows" and not c["safe_mode"] and "AUTOPREVIAS_NO_MEDIA" not in env


def test_cierres_seguidos_cambian_de_motor_y_luego_modo_seguro(tmp_path):
    f = tmp_path / "s.json"
    W.prepare(f, env={})                             # 1.º: se cierra de golpe (queda pendiente)
    env = {}
    c = W.prepare(f, env=env)
    assert env["QT_MEDIA_BACKEND"] == "ffmpeg" and not c["safe_mode"]
    env = {}
    c = W.prepare(f, env=env)                        # 2.º cierre: modo seguro
    assert c["safe_mode"] and env["AUTOPREVIAS_NO_MEDIA"] == "1" and env["AUTOPREVIAS_NO_ANIM"] == "1"
    W.mark_ok(f)
    c = W.prepare(f, env={})
    assert c["safe_mode"]                            # lo que funciona se conserva


def test_motor_bueno_se_conserva(tmp_path):
    f = tmp_path / "s.json"
    W.prepare(f, env={})
    env = {}
    W.prepare(f, env=env)
    W.mark_ok(f)
    env = {}
    c = W.prepare(f, env=env)
    assert env["QT_MEDIA_BACKEND"] == "ffmpeg" and not c["safe_mode"]


def test_respeta_un_motor_elegido_a_mano(tmp_path):
    env = {"QT_MEDIA_BACKEND": "ffmpeg"}
    W.prepare(tmp_path / "s.json", env=env)
    assert env["QT_MEDIA_BACKEND"] == "ffmpeg"


def test_estado_corrupto_no_rompe(tmp_path):
    f = tmp_path / "s.json"
    f.write_text("{no es json", encoding="utf-8")
    assert W.prepare(f, env={})["backend"] == "windows"
