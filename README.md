# Sistema de Gestión de Recursos Humanos

Plataforma integral de RRHH con **dashboard web**, API REST y base de datos local. Pensada para ejecutarse de forma **local** (sin servidor externo).

## Stack

- **Backend:** Python 3.12 + Django 6 + Django REST Framework
- **Base de datos:** SQLite (se genera sola) · MySQL opcional
- **Frontend:** Django templates + Bootstrap 5 + Chart.js (incluidos localmente)
- **Auth:** sesión web + JWT para la API

---

## 🚀 Instalación rápida (recomendada)

### Windows
1. Descomprimí el `.zip`.
2. Doble clic en **`iniciar.bat`** (o clic derecho → Ejecutar como administrador si falla).
3. El script hace TODO: crea el entorno, instala dependencias, genera la BD, carga usuarios y abre el navegador.

### PowerShell (alternativa)
```powershell
.\iniciar.ps1
```

### Manual
```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

> **Requiere:** Python 3.10+ instalado y conexión a internet **solo la primera vez** (para `pip install`).

---

## 👤 Usuarios de acceso (ya creados)

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `admin123` | Gerente de RRHH (acceso total) |
| `gerente` | `gerente123` | Gerente de RRHH |
| `rrhh` | `rrhh1234` | Administrativo de RRHH |
| `consulta` | `consulta1234` | Solo lectura |

Estos usuarios se crean **automáticamente** al ejecutar `migrate`.

---

## 🌐 URLs

| URL | Descripción |
|-----|-------------|
| `http://127.0.0.1:8000/` | Dashboard (login + panel) |
| `http://127.0.0.1:8000/admin/` | Administración Django |
| `http://127.0.0.1:8000/api/docs/` | Swagger (API REST) |
| `http://127.0.0.1:8000/api/reportes/` | Reportes (JSON / Excel / PDF) |

---

## 📦 Datos de demostración (opcional)

Para poblar el sistema con datos de ejemplo (empleados, unidades, puestos, incidencias):
```powershell
python manage.py cargar_demo
```

---

## 🧩 Módulos

Empleados · Estructura organizacional · Puestos y cargos · Designaciones · Legajo digital · Asistencia · Vacaciones y licencias · Evaluaciones · Sanciones · Incidencias · Vida laboral · Reportes

---

## 🗄️ Cambiar a MySQL (opcional)

1. Crear la base:
   ```sql
   CREATE DATABASE rrhh_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. En `.env` cambiar: `DB_ENGINE=mysql` y completar usuario/clave.
3. `python manage.py migrate`

---

## 🗂️ Estructura

```
config/          Configuración Django
apps/            Módulos (accounts, empleados, organizacion, puestos, asistencia,
                 licencias, evaluaciones, sanciones, incidencias, auditoria,
                 reportes, web)
static/          CSS/JS locales (Bootstrap, Chart.js)
templates/       (los templates web están en apps/web/templates)
AVANCES.md       Documento de avance/continuidad
iniciar.bat      Arranque automático (Windows)
iniciar.ps1      Arranque automático (PowerShell)
```

---

## 👨‍🎓 Para dividir entre 4 desarrolladores

Cada app en `apps/` es un módulo independiente → se reparten así:
- **Dev 1:** `accounts`, `empleados`, `organizacion`
- **Dev 2:** `puestos`, `asistencia`, `licencias`
- **Dev 3:** `evaluaciones`, `sanciones`, `incidencias`
- **Dev 4:** `reportes`, `auditoria`, `web`

Pasos: uno crea el repo en GitHub → los demás hacen `git clone` y suben su parte.

---

## 📝 Continuidad

Ver **`AVANCES.md`** para el estado del proyecto y el próximo paso.
