@echo off
TITLE Configuration du Service Serveur Ecole
echo ===================================================
echo   INSTALLATION DU SERVICE BACKEND WINDOWS (FASTAPI)
echo ===================================================

:: Chemins dynamiques basés sur le dossier du projet
set SERVICENAME=MonServeurEcole
set PYTHON_PATH=%~dp0venv\Scripts\python.exe
set PROJECT_DIR=%~dp0
set NSSM_PATH=%~dp0nssm.exe

:: Installation et configuration automatique via NSSM
"%NSSM_PATH%" install %SERVICENAME% "%PYTHON_PATH%" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
"%NSSM_PATH%" set %SERVICENAME% AppDirectory "%PROJECT_DIR%"
"%NSSM_PATH%" set %SERVICENAME% Start SERVICE_AUTO_START
"%NSSM_PATH%" start %SERVICENAME%

echo.
echo ===================================================
echo   SERVICE INSTALLE ET DEMARRE AVEC SUCCES !
echo ===================================================
pause