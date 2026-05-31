"""
CHARAMOU AI - Build en .exe autonome via PyInstaller
Usage : python scripts/build_exe.py
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent

PYINSTALLER_CMD = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--name=CHARAMOU_AI",
    f"--icon={ROOT / 'interfaces' / 'gui' / 'assets' / 'icon.ico'}",
    "--add-data", f"{ROOT / 'config'};config",
    "--add-data", f"{ROOT / 'data' / 'voices'};data/voices",
    "--hidden-import=pyttsx3.drivers",
    "--hidden-import=pyttsx3.drivers.sapi5",
    "--hidden-import=speech_recognition",
    "--hidden-import=openai",
    "--hidden-import=customtkinter",
    str(ROOT / "launcher.py")
]


def build():
    print("=" * 50)
    print("  CHARAMOU AI - Génération du .exe")
    print("=" * 50)

    try:
        import PyInstaller
        print(f"PyInstaller {PyInstaller.__version__} trouvé.")
    except ImportError:
        print("PyInstaller non installé. Exécutez : pip install pyinstaller")
        sys.exit(1)

    os.chdir(ROOT)
    print("Lancement de PyInstaller...")

    result = subprocess.run(PYINSTALLER_CMD, check=False)

    if result.returncode == 0:
        exe_path = ROOT / "dist" / "CHARAMOU_AI.exe"
        print(f"\n✅ Build réussi !")
        print(f"   Exécutable : {exe_path}")
    else:
        print("\n❌ Build échoué — consultez les logs PyInstaller ci-dessus.")
        sys.exit(1)


if __name__ == "__main__":
    build()
