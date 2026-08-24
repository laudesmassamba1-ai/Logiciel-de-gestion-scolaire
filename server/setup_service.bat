@echo off
TITLE Configuration du Service Serveur Ecole
echo ===================================================
echo   INSTALLATION DU SERVICE BACKEND WINDOWS (FASTAPI)
echo ===================================================

:: Chemins dynamiques bases sur le dossier du projet
set SERVICENAME=MonServeurEcole
set PYTHON_PATH=%~dp0venv\Scripts\python.exe
set PROJECT_DIR=%~dp0
set NSSM_PATH=%~dp0nssm.exe
set ENV_FILE=%~dp0.env

:: -----------------------------------------------------------
:: Generation du fichier .env (configuration MySQL)
:: Le serveur charge ce fichier au demarrage (voir securite.py).
:: -----------------------------------------------------------
if exist "%ENV_FILE%" goto env_ok

echo.
echo Configuration de la base de donnees MySQL :
set /p DB_HOST=Host MySQL [localhost] :
set /p DB_USER=Utilisateur MySQL [root] :
set /p DB_PASS=Mot de passe MySQL (obligatoire) :
set /p DB_NAME=Nom de la base [ecole] :

if "%DB_HOST%"=="" set DB_HOST=localhost
if "%DB_USER%"=="" set DB_USER=root
if "%DB_NAME%"=="" set DB_NAME=ecole
if "%DB_PASS%"=="" (
    echo [ERREUR] Le mot de passe MySQL est obligatoire.
    echo          Renseignez GS_DB_PASSWORD dans %ENV_FILE% puis relancez.
    pause
    exit /b 1
)

(
    echo GS_DB_HOST=%DB_HOST%
    echo GS_DB_USER=%DB_USER%
    echo GS_DB_PASSWORD=%DB_PASS%
    echo GS_DB_NAME=%DB_NAME%
)> "%ENV_FILE%"
echo [OK] Fichier .env cree.

:env_ok
:: -----------------------------------------------------------
:: Installation et configuration automatique via NSSM
:: -----------------------------------------------------------
"%NSSM_PATH%" install %SERVICENAME% "%PYTHON_PATH%" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
"%NSSM_PATH%" set %SERVICENAME% AppDirectory "%PROJECT_DIR%"
"%NSSM_PATH%" set %SERVICENAME% Start SERVICE_AUTO_START
"%NSSM_PATH%" start %SERVICENAME%

echo.
echo ===================================================
echo   SERVICE INSTALLE ET DEMARRE AVEC SUCCES !
echo   Piste d'audit disponible sur GET /audit (admin).
echo ===================================================
pause
