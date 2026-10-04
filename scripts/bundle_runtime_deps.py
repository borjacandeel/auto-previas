#!/usr/bin/env python3
"""
bundle_runtime_deps.py
Copia dependencias de tiempo de ejecución de librosa al bundle standalone de Nuitka
y soluciona paths de bibliotecas nativas para codesign en macOS.
"""

import sys
import os
import shutil
import glob
import subprocess
import site

PACKAGES_TO_BUNDLE = [
    "librosa",
    "numba",
    "llvmlite",
    "decorator",
    "joblib",
    "msgpack",
    "cloudpickle",
    "pooch",
    "platformdirs",
    "requests",
    "urllib3",
    "certifi",
    "idna",
    "charset_normalizer",
    "packaging",
    "sklearn",
    "scikit_learn.libs",
    "threadpoolctl",
    "narwhals",
]

def find_package_path(pkg_name):
    try:
        mod = __import__(pkg_name)
        if hasattr(mod, "__path__"):
            return mod.__path__[0]
        elif hasattr(mod, "__file__") and mod.__file__:
            return mod.__file__
    except Exception:
        pass

    for sp in site.getsitepackages():
        candidate_dir = os.path.join(sp, pkg_name)
        if os.path.isdir(candidate_dir):
            return candidate_dir
        candidate_file = os.path.join(sp, pkg_name + ".py")
        if os.path.isfile(candidate_file):
            return candidate_file
    return None

def bundle_dependencies(target_dir):
    print(f"[*] Empaquetando dependencias de runtime en: {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    for pkg in PACKAGES_TO_BUNDLE:
        src = find_package_path(pkg)
        if not src or not os.path.exists(src):
            print(f"    [-] Omitiendo {pkg} (no encontrado en site-packages)")
            continue

        base_name = os.path.basename(src)
        dest = os.path.join(target_dir, base_name)

        if os.path.isdir(src):
            print(f"    [+] Sincronizando directorio {pkg}...")
            shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif os.path.isfile(src):
            print(f"    [+] Copiando módulo {base_name}...")
            shutil.copy2(src, dest)

    if sys.platform == "darwin":
        sklearn_dir = os.path.join(target_dir, "sklearn")
        old_dylibs = os.path.join(sklearn_dir, ".dylibs")
        new_dylibs = os.path.join(sklearn_dir, "dylibs")

        if os.path.exists(old_dylibs):
            print("    [!] Renombrando sklearn/.dylibs a sklearn/dylibs para Apple codesign...")
            if os.path.exists(new_dylibs):
                shutil.rmtree(new_dylibs)
            os.rename(old_dylibs, new_dylibs)

        for so in glob.glob(os.path.join(sklearn_dir, "**", "*.so"), recursive=True):
            try:
                out = subprocess.check_output(["otool", "-L", so]).decode()
                for line in out.splitlines():
                    if ".dylibs/libomp.dylib" in line:
                        old_ref = line.strip().split()[0]
                        new_ref = old_ref.replace(".dylibs/libomp.dylib", "dylibs/libomp.dylib")
                        subprocess.check_call(["install_name_tool", "-change", old_ref, new_ref, so])
            except Exception as e:
                print(f"    [!] Advertencia al actualizar {so}: {e}")

    print("[*] Empaquetado de dependencias completado con éxito.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python bundle_runtime_deps.py <directorio_destino>")
        sys.exit(1)
    bundle_dependencies(sys.argv[1])
