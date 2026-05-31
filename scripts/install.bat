@echo off
REM ============================================================
REM  CHARAMOU AI - Script d'installation Windows
REM ============================================================

echo.
echo  ==========================================
echo   CHARAMOU AI - Installation
echo  ==========================================
echo.

REM Vérification Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python non trouvé. Installez Python 3.9+ depuis https://python.org
    pause
    exit /b 1
)
echo [OK] Python trouvé.

REM Création environnement virtuel
IF NOT EXIST "venv\" (
    echo Création de l'environnement virtuel...
    python -m venv venv
)
echo [OK] Environnement virtuel prêt.

REM Activation
call venv\Scripts\activate.bat

REM Mise à jour pip
python -m pip install --upgrade pip --quiet

REM Installation des dépendances
echo Installation des dépendances...
pip install -r requirements.txt --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo [ATTENTION] Certains paquets ont échoué - vérifiez requirements.txt
)
echo [OK] Dépendances installées.

REM Création .env si absent
IF NOT EXIST ".env" (
    IF EXIST ".env.example" (
        copy .env.example .env >nul
        echo [INFO] Fichier .env créé - configurez vos clés API dans .env
    )
)

REM Création des répertoires nécessaires
IF NOT EXIST "logs\" mkdir logs
IF NOT EXIST "data\cache\" mkdir data\cache
IF NOT EXIST "data\temp\" mkdir data\temp
IF NOT EXIST "data\models\" mkdir data\models
IF NOT EXIST "database\" mkdir database
echo [OK] Répertoires créés.

echo.
echo  ==========================================
echo   Installation terminée !
echo   Lancez l'assistant avec : start_assistant.bat
echo  ==========================================
echo.
pause
