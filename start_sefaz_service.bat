@echo off
title SEFAZ Service - Uvicorn Starter
echo ================================================
echo    INICIANDO SEFAZ SERVICE (FastAPI + Uvicorn)
echo ================================================

:: Caminho base do projeto (ajuste se necessário)
set PROJECT_DIR=C:\PROJETOS\sefaz_service

:: Nome da pasta do venv
set VENV_NAME=venv

echo.
echo [1/4] Acessando pasta do projeto...
cd /d "%PROJECT_DIR%"

echo.
echo [2/4] Ativando ambiente virtual...
if exist "%PROJECT_DIR%\%VENV_NAME%\Scripts\activate.bat" (
    call "%PROJECT_DIR%\%VENV_NAME%\Scripts\activate.bat"
    echo Ambiente virtual ativado com sucesso.
) else (
    echo Ambiente virtual NAO ENCONTRADO!
    echo Criando novo ambiente virtual...
    python -m venv "%VENV_NAME%"
    call "%PROJECT_DIR%\%VENV_NAME%\Scripts\activate.bat"
)

echo.
echo [3/4] Instalando dependencias (requirements.txt)...
if exist "%PROJECT_DIR%\requirements.txt" (
    pip install -r requirements.txt
) else (
    echo "requirements.txt NAO encontrado! Continuando mesmo assim..."
)

echo.
echo [4/4] Iniciando Uvicorn com reload automático...
echo.
echo Abra no navegador: http://127.0.0.1:8000/docs
echo.

:: Abrir Swagger automaticamente (opcional)
start "" http://127.0.0.1:8000/docs

:: Iniciar servidor
uvicorn sefaz_api.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Servidor finalizado.
pause
