@echo off
setlocal

REM ============================================================
REM Installation automatique du service Windows pour la synchro
REM À lancer en tant qu'ADMINISTRATEUR, depuis le dossier où se
REM trouvent nssm.exe, sync_engine.py, sync_pull.py, sync_queue.py,
REM database.py et config.json.
REM ============================================================

set SERVICE_NAME=SyncEngineEcole
set SCRIPT_DIR=%~dp0
set NSSM_PATH=%SCRIPT_DIR%nssm.exe

REM  Adapte ce chemin si ton environnement virtuel n'est pas
REM    dans un sous-dossier "venv" à côté de ce fichier .bat
set PYTHON_PATH=%SCRIPT_DIR%venv\Scripts\python.exe

if not exist "%NSSM_PATH%" (
    echo [ERREUR] nssm.exe introuvable dans %SCRIPT_DIR%
    echo Place nssm.exe dans ce dossier avant de relancer ce script.
    pause
    exit /b 1
)

if not exist "%PYTHON_PATH%" (
    echo [ERREUR] python.exe introuvable a l'emplacement :
    echo %PYTHON_PATH%
    echo Modifie la ligne PYTHON_PATH dans ce fichier .bat pour le bon chemin.
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo Installation du service %SERVICE_NAME%...
"%NSSM_PATH%" install %SERVICE_NAME% "%PYTHON_PATH%" "sync_engine.py"

echo Configuration du dossier de travail...
"%NSSM_PATH%" set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"

echo Configuration des journaux (logs)...
"%NSSM_PATH%" set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%logs\sync_out.log"
"%NSSM_PATH%" set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%logs\sync_err.log"

echo Configuration du demarrage automatique...
"%NSSM_PATH%" set %SERVICE_NAME% Start SERVICE_AUTO_START

echo Demarrage du service...
"%NSSM_PATH%" start %SERVICE_NAME%

echo.
echo ============================================================
echo Termine. Verifie dans "Services" (services.msc) que
echo %SERVICE_NAME% est bien "En cours d'execution".
echo Les journaux se trouvent dans : %SCRIPT_DIR%logs
echo ============================================================
pause