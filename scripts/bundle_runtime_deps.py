#!/usr/bin/env python3
"""
bundle_runtime_deps.py
Copia dependencias de tiempo de ejecucion de librosa al bundle standalone de Nuitka
y soluciona paths de bibliotecas nativas para codesign en macOS.
"""

import sys
import os
import shutil
import glob
import subprocess
import site

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
            print(f"    [+] Copiando modulo {base_name}...")
            shutil.copy2(src, dest)

    # Asegurar módulos y extensiones estándar críticos requeridos por Numba/Librosa
    import sysconfig
    stdlib_dir = sysconfig.get_path("stdlib")
    if stdlib_dir and os.path.isdir(stdlib_dir):
        for mod_name in ["uuid.py", "dis.py", "inspect.py", "opcode.py"]:
            src_mod = os.path.join(stdlib_dir, mod_name)
            dst_mod = os.path.join(target_dir, mod_name)
            if os.path.isfile(src_mod) and not os.path.exists(dst_mod):
                print(f"    [+] Copiando modulo stdlib crítico: {mod_name}")
                shutil.copy2(src_mod, dst_mod)

        dynload_dirs = [
            os.path.join(stdlib_dir, "lib-dynload"),
            os.path.join(os.path.dirname(stdlib_dir), "DLLs"),
            os.path.join(sys.prefix, "DLLs"),
        ]
        for d in dynload_dirs:
            if os.path.isdir(d):
                for pattern in ["*uuid*", "*opcode*"]:
                    for f in glob.glob(os.path.join(d, pattern)):
                        dst_f = os.path.join(target_dir, os.path.basename(f))
                        if not os.path.exists(dst_f):
                            print(f"    [+] Copiando extension stdlib crítica: {os.path.basename(f)}")
                            shutil.copy2(f, dst_f)

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

    # Sincronizar plugins multimedia de PySide6 para reproducción nativa de audio
    print("[*] Sincronizando plugins multimedia de PySide6...")
    for sp in site.getsitepackages():
        qt_mm_src = os.path.join(sp, "PySide6", "Qt", "plugins", "multimedia")
        if os.path.isdir(qt_mm_src):
            for rel_sub in [os.path.join("PySide6", "qt-plugins", "multimedia"), os.path.join("PySide6", "plugins", "multimedia")]:
                dest_mm = os.path.join(target_dir, rel_sub)
                os.makedirs(dest_mm, exist_ok=True)
                for item in os.listdir(qt_mm_src):
                    s_file = os.path.join(qt_mm_src, item)
                    d_file = os.path.join(dest_mm, item)
                    if os.path.isfile(s_file) and not os.path.exists(d_file):
                        shutil.copy2(s_file, d_file)
                        print(f"    [+] Copiado plugin multimedia: {item} -> {rel_sub}")

            if sys.platform == "darwin":
                qt_mapping = {
                    "@rpath/QtMultimedia.framework/Versions/A/QtMultimedia": "@executable_path/QtMultimedia",
                    "@rpath/QtCore.framework/Versions/A/QtCore": "@executable_path/QtCore",
                    "@rpath/QtGui.framework/Versions/A/QtGui": "@executable_path/QtGui",
                    "@rpath/QtNetwork.framework/Versions/A/QtNetwork": "@executable_path/QtNetwork",
                    "@rpath/QtConcurrent.framework/Versions/A/QtConcurrent": "@executable_path/QtConcurrent",
                }
                for rel_sub in [os.path.join("PySide6", "qt-plugins", "multimedia"), os.path.join("PySide6", "plugins", "multimedia")]:
                    dest_mm = os.path.join(target_dir, rel_sub)
                    for dylib in glob.glob(os.path.join(dest_mm, "*.dylib")):
                        for old_ref, new_ref in qt_mapping.items():
                            subprocess.call(["install_name_tool", "-change", old_ref, new_ref, dylib], stderr=subprocess.DEVNULL)
                        subprocess.call(["install_name_tool", "-add_rpath", "@executable_path", dylib], stderr=subprocess.DEVNULL)
    # Precompilar todos los archivos .py a .pyc para evitar intentos de escritura en tiempo de ejecución en Program Files
    print("[*] Precompilando bytecode de módulos de Python...")
    import compileall
    compileall.compile_dir(target_dir, force=False, quiet=1)

    print("[*] Empaquetado de dependencias completado con exito.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python bundle_runtime_deps.py <directorio_destino>")
        sys.exit(1)
    bundle_dependencies(sys.argv[1])
