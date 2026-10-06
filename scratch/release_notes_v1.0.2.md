# AutoPrevias v1.0.2 — Parche Oficial de Compatibilidad de llvmlite en Windows

Tercera entrega oficial y parche de estabilidad para la ejecución autónoma de AutoPrevias en Windows x64 y macOS Apple Silicon.

## 📦 Descarga de Instaladores Oficiales

| Plataforma | Arquitectura | Archivo Instalador | Tipo de Paquete |
| :--- | :--- | :--- | :--- |
| 🍏 **macOS** | **Apple Silicon (M1 / M2 / M3 / M4)** | `AutoPrevias-1.0.2-macOS-arm64.dmg` | Imagen de disco arrastrable a Aplicaciones |
| 🪟 **Windows** | **64-bit (x64)** | `AutoPrevias-Windows-x64-Setup.exe` | Instalador asistido Inno Setup con accesos directos |

---

## 🔧 Correcciones Técnicas del Parche (v1.0.2)

- **Carga de bibliotecas nativas C de LLVM en Windows (`llvmlite.dll`):**
  - **Problema corregido:** En Windows x64, la invocación de `librosa` arrojaba `OSError: Could not find/load shared object file 'llvmlite.dll' from resource location: 'llvmlite.binding'`.
  - **Causa raíz:** `llvmlite` utiliza `importlib.resources` para resolver dinámicamente mediante `ctypes.CDLL` la librería compilada de LLVM. En bundles de Nuitka, el archivo binario DLL no se encontraba en la ruta de recursos de paquete esperada por el importador.
  - **Solución implementada:** Se integró en el flujo de CI de Windows un paso post-compilación en PowerShell que localiza `llvmlite.dll` y lo sitúa tanto en `llvmlite/binding/` como en la ruta raíz del paquete. Adicionalmente, se configuró Nuitka con `--include-package-data=llvmlite`.
  - **Verificación:** Superación del 100% de las pruebas del auto-diagnóstico `--selftest` en Windows y macOS.

---

## 🛡️ Instrucciones de Instalación

### 🍏 macOS (Apple Silicon arm64)
1. Descarga el archivo `AutoPrevias-1.0.2-macOS-arm64.dmg` (o el enlace genérico `AutoPrevias-macOS-arm64.dmg`).
2. Abre la imagen `.dmg` y arrastra **AutoPrevias** a la carpeta de **Aplicaciones**.
3. *Aviso de Gatekeeper (primera apertura):* Si macOS muestra la advertencia de desarrollador no verificado, haz clic derecho sobre la app y selecciona **Abrir**, o ejecuta en Terminal:
   ```bash
   xattr -cr /Applications/AutoPrevias.app
   ```

### 🪟 Windows (10 y 11 de 64 bits)
1. Descarga `AutoPrevias-Windows-x64-Setup.exe`.
2. Ejecuta el archivo y sigue los pasos del asistente de instalación.
3. Se generarán accesos directos en el Escritorio y Menú Inicio.

---

## 🔒 Verificación de Integridad SHA-256
Puedes contrastar el hash de los instaladores descargados con el archivo `SHA256SUMS.txt` adjunto a esta release:
- **macOS:** `shasum -a 256 AutoPrevias-macOS-arm64.dmg`
- **Windows:** `Get-FileHash -Algorithm SHA256 AutoPrevias-Windows-x64-Setup.exe`
