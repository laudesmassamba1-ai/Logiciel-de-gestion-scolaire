@echo off
setlocal

REM ============================================================
REM Installation automatique du service Windows pour la synchro
REM À lancer en tant qu'ADMINISTRATEUR
REM ============================================================

set SERVICE_NAME=SyncEngineEcole
set SCRIPT_DIR=%~dp0
set NSSM_PATH=%SCRIPT_DIR%nssm.exe
set PYTHON_PATH=%SCRIPT_DIR%venv\Scripts\python.exe

REM 1. Vérification des privilèges Administrateur
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR CRITIQUE] Ce script doit absolument etre lance en tant qu'Administrateur !
    echo Clic droit sur le fichier .bat et choisis "Executer en tant d'administrateur".
    pause
    exit /b 1
)

REM 2. Vérification de la présence de nssm.exe
if not exist "%NSSM_PATH%" (
    echo [ERREUR] nssm.exe est introuvable dans : %SCRIPT_DIR%
    echo Place nssm.exe dans ce dossier avant de relancer.
    pause
    exit /b 1
)

REM 3. Vérification de l'environnement virtuel Python
if not exist "%PYTHON_PATH%" (
    echo [ERREUR] python.exe est introuvable dans l'environnement virtuel :
    echo %PYTHON_PATH%
    echo Verifie le chemin ou cree le venv avant de continuer.
    pause
    exit /b 1
)

REM 4. Création du dossier de logs si absent
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

REM 5. Gestion si le service existe déjà
sc query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Le service %SERVICE_NAME% existe deja. Suppression de l'ancienne instance...
    "%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>&1
    "%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>&1
)

echo [1/6] Installation du service %SERVICE_NAME%...
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_PATH%" "sync_engine.py"
if %errorlevel% neq 0 goto erreur

echo [2/6] Configuration du dossier de travail (AppDirectory)...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%SCRIPT_DIR%"
if %errorlevel% neq 0 goto erreur

echo [3/6] Configuration des journaux (logsout et logserr)...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%SCRIPT_DIR%logs\sync_out.log"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%SCRIPT_DIR%logs\sync_err.log"
if %errorlevel% neq 0 goto erreur

echo [4/6] Activation de la rotation automatique des logs (max 5 Mo)...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateFiles 1
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateBytes 5242880
if %errorlevel% neq 0 goto erreur

echo [5/6] Configuration du demarrage automatique...
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
if %errorlevel% neq 0 goto erreur

echo [6/6] Demarrage du service de synchronisation...
"%NSSM_PATH%" start "%SERVICE_NAME%"
if %errorlevel% neq 0 goto erreur

echo.
echo ============================================================
echo [SUCCES] Installation terminee avec succes !
echo Verifie dans "Services" (services.msc) que le service
echo "%SERVICE_NAME%" est bien "En cours d'execution".
echo Les journaux se trouvent dans : %SCRIPT_DIR%logs
echo ============================================================
pause
exit /b 0

:erreur
echo.
echo [ERREUR] Une erreur est survenue pendant la configuration NSSM.
echo Verifie les messages ci-dessus.
pause
exit /b 1