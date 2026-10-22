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
| `http://127.0.0.1:8000/mis-licencias/` | Autoservicio para usuarios vinculados a un empleado |
| `http://127.0.0.1:8000/asistencia/fichar/` | Fichaje personal de entrada y salida |
| `http://127.0.0.1:8000/asistencia/importar/` | Importación de marcaciones y cierre diario (RR. HH.) |
| `http://127.0.0.1:8000/admin/` | Administración Django |
| `http://127.0.0.1:8000/api/docs/` | Swagger (API REST) |
| `http://127.0.0.1:8000/api/asistencia/` | API de horarios diarios, turnos, jornadas, marcaciones y cierres |
| `http://127.0.0.1:8000/api/reportes/` | Reportes (JSON / Excel / PDF) |
| `http://127.0.0.1:8000/api/capacitaciones/` | Cursos, inscripciones, asistencias y certificados |

---

## 📦 Datos de demostración (opcional)

Para poblar el sistema con datos de ejemplo (empleados, unidades, puestos, incidencias):
```powershell
python manage.py cargar_demo
python manage.py cargar_asistencia_demo
```

Para cerrar la asistencia del día anterior, o una fecha/rango concreto:
```powershell
python manage.py cerrar_asistencia
python manage.py cerrar_asistencia --fecha 2026-10-14
python manage.py cerrar_asistencia --desde 2026-10-01 --hasta 2026-10-14
```

El cierre diario consolida las marcaciones, crea registros de licencia o vacaciones
solicitadas y genera ausencias en días laborables sin marcaciones. Las vacaciones no
generan registros en fines de semana ni feriados; si alguien ficha durante una licencia,
se conservan sus marcaciones y se agrega una observación. Control de Asistencia permite
filtrar por fecha y muestra a todos los empleados activos: sus marcaciones registradas,
las solicitudes de licencia/vacaciones del rango, sin depender de su estado de aprobación,
y, si no aplica ninguna, el estado ausente en días laborables. Si un ausente automático
obtiene una solicitud de licencia antes de volver a cerrar ese día,
su estado se actualiza. La lista permite filtrar por nombre o legajo; al abrir un empleado
se muestra el resumen del mes con asistencias, ausencias, horas extra, licencias,
vacaciones e incidencias/avisos. Los totales de vacaciones y licencias usan los días
solicitados guardados en cada solicitud y también se muestran en el detalle de cada una.
Para ejecutarlo sin intervención,
ejecuta una sola vez `python manage.py programar_cierre_asistencia` en Windows.
Esto registra una tarea diaria a las 00:00 y la reintenta cuando el equipo vuelve
a estar disponible; requiere mantener abierta la sesión de Windows del usuario que
la programó. El botón **Día terminado** en Asistencia cierra manualmente el
día actual; el cierre automático de medianoche procesa el día anterior. En Linux/cron,
por ejemplo, prográmalo cada día a las 00:10:
```cron
10 0 * * * cd /ruta/al/proyecto && /ruta/al/proyecto/venv/bin/python manage.py cerrar_asistencia
```

### Reglas de cálculo de asistencia

La tolerancia se descuenta del retraso: solo los minutos posteriores al horario esperado
más la tolerancia se guardan como tardanza. El horario diario usa la tolerancia global
configurable; las jornadas conservan la tolerancia de `Jornada` o de `Turno`, según su
origen. Esta regla de tardanza es una decisión de negocio revisable.

El mínimo de horas extra depende actualmente del origen del horario: `HorarioDiario`
aplica el mínimo global configurable (30 minutos por defecto), mientras que una `Jornada`
conserva la regla histórica de contar cualquier exceso positivo. Esta diferencia es una
decisión pendiente de unificar. Los turnos nocturnos asignan la salida fichada del día
siguiente al horario del día de inicio. El tipo `Feriado` no diferencia feriados
obligatorios de días no laborables; ambos usan por ahora el mismo cálculo.

### Horario predeterminado y excepciones por fecha

En la carga de horarios, la primera fecha con horario de un empleado establece
su horario predeterminado desde esa fecha. Se aplica a los días laborables
definidos por la Jornada del empleado; los días sin jornada laborable siguen
sin horario automático. Las cargas posteriores pueden dejar una excepción
`HorarioDiario` para una sola fecha o cambiar el predeterminado desde esa fecha.
Una excepción diaria prevalece ese día y luego vuelve a aplicarse el
predeterminado. Al cambiarlo se reemplazan versiones predeterminadas futuras,
pero se conservan las anteriores para no alterar el historial.

La importación acepta CSV y XLSX de hasta 5 MB y 20.000 filas. El archivo requiere
`legajo` y `fecha_hora`, o `legajo`, `fecha` y `hora`; `tipo` (ENTRADA/SALIDA o E/S)
es opcional. Sin `tipo`, se toma la primera marcación del día como entrada y la última
como salida.

---

## 🧩 Módulos

Empleados · Estructura organizacional · Puestos y cargos · Designaciones · Legajo digital · Asistencia (fichaje web, jornadas, turnos, feriados, importación CSV/XLSX y cierre diario) · Vacaciones y licencias · Evaluaciones ponderadas · Sanciones con flujo de propuesta, notificación, aplicación y apelación · Incidencias con transiciones controladas · Capacitaciones · Vida laboral · Reportes

Las solicitudes cuentan días hábiles de lunes a viernes, excluyendo los feriados cargados en el módulo de asistencia. El derecho anual de vacaciones usa la antigüedad al 31 de diciembre y la escala de 14, 21, 28 o 35 días.

Las evaluaciones aceptan calificaciones entre 0 y 100 y calculan su resultado con el promedio ponderado de los criterios. Se pueden consultar comparaciones con el período anterior desde el endpoint de la evaluación. Los certificados de capacitación se emiten al completar el mínimo de asistencia configurado y quedan asociados al legajo digital del empleado.

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
