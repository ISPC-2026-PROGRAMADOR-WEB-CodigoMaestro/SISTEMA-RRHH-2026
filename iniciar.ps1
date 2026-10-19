# ============================================================
#  Sistema de Gestion de Recursos Humanos - Arranque automatico
# ============================================================
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   SISTEMA DE GESTION DE RECURSOS HUMANOS" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$py = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $py = @('py', '-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $py = @('python') }
else {
    Write-Host "ERROR: No se encontro Python. Instala Python 3.10+ y vuelve a intentar." -ForegroundColor Red
    Read-Host "Presiona ENTER para salir"
    exit 1
}

if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "[1/4] Creando entorno virtual..." -ForegroundColor Yellow
    & $py[0] $py[1..($py.Length-1)] -m venv venv
}
else {
    Write-Host "[1/4] El entorno virtual ya existe." -ForegroundColor Green
}

Write-Host "[2/4] Instalando dependencias (la primera vez demora)..." -ForegroundColor Yellow
& venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "[3/4] Preparando la base de datos y los usuarios..." -ForegroundColor Yellow
& venv\Scripts\python.exe manage.py migrate
& venv\Scripts\python.exe manage.py collectstatic --noinput | Out-Null

Write-Host "[4/4] Iniciando el servidor..." -ForegroundColor Green
Write-Host ""
Write-Host "   El navegador se abrira automaticamente en la pantalla de login." -ForegroundColor White
Write-Host ""
Write-Host "   Usuarios de acceso:" -ForegroundColor White
Write-Host "     admin     / admin123      (Gerente - total)"
Write-Host "     gerente   / gerente123    (Gerente)"
Write-Host "     rrhh      / rrhh1234      (Administrativo)"
Write-Host "     consulta  / consulta1234  (Solo lectura)"
Write-Host ""
Write-Host "   Para APAGAR el sistema: presiona CTRL+C en esta ventana." -ForegroundColor White
Write-Host ""

# Espera a que el servidor responda y luego abre el navegador en el login
Start-Job -ScriptBlock {
    while ($true) {
        try {
            Invoke-WebRequest -Uri 'http://127.0.0.1:8000/login/' -UseBasicParsing -TimeoutSec 2 | Out-Null
            break
        } catch { Start-Sleep -Milliseconds 700 }
    }
    Start-Process 'http://127.0.0.1:8000/login/'
} | Out-Null

& venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
