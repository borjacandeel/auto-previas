"""Tests de la lógica pura del actualizador (sin Qt ni red)."""
import hashlib

from src.updater_core import (
    installer_asset_name, is_newer, parse_release, parse_sha256sums,
    parse_version, sha256_file, strip_links,
)


def test_parse_version():
    assert parse_version("v2.9.7") == (2, 9, 7)
    assert parse_version("2.10.0") == (2, 10, 0)
    assert parse_version("basura") is None
    assert parse_version(None) is None


def test_is_newer_compara_numericamente():
    assert is_newer("2.10.0", "2.9.9")
    assert is_newer("v3.0.0", "2.9.7")
    assert not is_newer("2.9.7", "2.9.7")
    assert not is_newer("2.9.6", "2.9.7")
    assert not is_newer("roto", "2.9.7")


def test_parse_release_ok_y_descarta_borradores():
    data = {
        "tag_name": "v2.9.8",
        "body": "Novedades",
        "html_url": "https://github.com/x/y/releases/tag/v2.9.8",
        "assets": [
            {"name": "SHA256SUMS.txt", "browser_download_url": "https://e/sums"},
            {"name": "AutoPrevias-Plus-macOS-arm64.dmg", "browser_download_url": "https://e/dmg"},
        ],
    }
    info = parse_release(data)
    assert info.version == "2.9.8"
    assert info.assets["AutoPrevias-Plus-macOS-arm64.dmg"] == "https://e/dmg"
    assert parse_release({**data, "draft": True}) is None
    assert parse_release({**data, "prerelease": True}) is None
    assert parse_release({"tag_name": "nightly"}) is None


def test_installer_asset_name():
    assert installer_asset_name("plus", "darwin", "arm64") == "AutoPrevias-Plus-macOS-arm64.dmg"
    assert installer_asset_name("basic", "darwin", "arm64") == "AutoPrevias-Basic-macOS-arm64.dmg"
    assert installer_asset_name("plus", "darwin", "x86_64") is None
    assert installer_asset_name("plus", "win32", "AMD64") == "AutoPrevias-Plus-Windows-x64-Setup.exe"
    assert installer_asset_name("", "win32", "AMD64") == "AutoPrevias-Basic-Windows-x64-Setup.exe"
    assert installer_asset_name("plus", "linux", "x86_64") is None


def test_parse_sha256sums_y_sha256_file(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"autoprevias")
    digest = hashlib.sha256(b"autoprevias").hexdigest()
    assert sha256_file(f) == digest
    sums = parse_sha256sums(f"{digest}  a.bin\n{digest.upper()} *b.bin\nlinea invalida\n")
    assert sums == {"a.bin": digest, "b.bin": digest}


def test_strip_links_no_deja_urls():
    t = strip_links("Mira [el enlace](https://github.com/x/y) y https://example.com/z fin")
    assert "http" not in t and "github" not in t and "el enlace" in t and t.endswith("fin")
    assert strip_links(None) == ""
