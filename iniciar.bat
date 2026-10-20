@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Sistema de Gestion de Recursos Humanos
echo Inicio: %date% %time% > "%~dp0iniciar_log.txt" 2>&1

echo ============================================================
echo    SISTEMA DE GESTION DE RECURSOS HUMANOS
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

if not exist "venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual...
    %PY% -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: No se pudo crear el entorno virtual. Verifica que Python 3.10+ este instalado.
        pause
        exit /b 1
    )
) else (
    echo [1/4] Entorno virtual ya existe.
)

echo [2/4] Instalando dependencias (la primera vez puede tardar unos minutos)...
call venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>nul
call venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR al instalar dependencias. Verifica tu conexion a internet.
    pause
    exit /b 1
)

if not exist ".env" (
    copy ".env.example" ".env" >nul
)

echo [3/4] Preparando la base de datos y los usuarios...
call venv\Scripts\python.exe manage.py migrate
call venv\Scripts\python.exe manage.py collectstatic --noinput >nul 2>nul

echo [4/4] Iniciando el servidor...
echo.
echo   El navegador se abrira automaticamente en la pantalla de login.
echo.
echo   Usuarios de acceso:
echo     admin     / admin123      (Gerente - total)
echo     gerente   / gerente123    (Gerente)
echo     rrhh      / rrhh1234      (Administrativo)
echo     consulta  / consulta1234  (Solo lectura)
echo.
echo   Para APAGAR el sistema: presiona CTRL+C en esta ventana.
echo.

rem Espera a que el servidor responda y abre el navegador en el login
start "" powershell -NoProfile -WindowStyle Hidden -Command "while ($true) { try { Invoke-WebRequest -Uri 'http://127.0.0.1:8000/login/' -UseBasicParsing -TimeoutSec 2 | Out-Null; break } catch { Start-Sleep -Milliseconds 700 } }; Start-Process 'http://127.0.0.1:8000/login/'"

call venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
