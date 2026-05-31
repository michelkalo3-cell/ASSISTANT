@echo off
REM ============================================================
REM  CHARAMOU AI - Démarrage de l'assistant
REM ============================================================

cd /d "%~dp0.."

IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo  Démarrage de CHARAMOU AI...
echo  Appuyez sur Ctrl+C pour arrêter.
echo.

python launcher.py

pause
