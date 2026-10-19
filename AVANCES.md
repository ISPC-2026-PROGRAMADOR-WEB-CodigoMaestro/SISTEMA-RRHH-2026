# AVANCES – Sistema de Gestion de Recursos Humanos

> **Documento de continuidad.** Si la terminal se cuelga, leé este archivo y retomá desde **Proximo paso**.

---

## Estado general

| Campo | Valor |
|---|---|
| **Fecha inicio** | 2022-07-10 |
| **Ultima actualizacion** | 2022-07-10 |
| **Fases completadas** | Fase 0, 1, 2, 3, 4, 5, 6 |
| **Fase actual** | Sistema completo + dashboard web (listo para feria) |
| **Estado del proyecto** | EN PROGRESO |
| **Stack** | Python 3.12 + Django 6.1.2 + DRF + MySQL/SQLite |
| **Entorno virtual** | `venv/` |
| **BD actual (.env)** | `DB_ENGINE=sqlite` |
| **Superusuario (dev)** | `admin` / `admin123` |

---

## Fases

| # | Fase | Estado |
|---|---|---|
| 0 | Setup proyecto | COMPLETADA |
| 1 | Modelo de datos + migraciones + admin + seeds | COMPLETADA |
| 2 | Seguridad, roles, JWT, API REST, auditoria | COMPLETADA |
| 3 | API empleados, legajo, organizacion | COMPLETADA |
| 4 | API puestos, designaciones, planta funcional, historial | COMPLETADA |
| 5 | API asistencia, licencias, evaluaciones, sanciones, incidencias | COMPLETADA |
| 6 | Reportes PDF/Excel y promociones potenciales | COMPLETADA |
| 7 | Tests formales y documentacion final | PENDIENTE |

---

## Fase 2 – Seguridad y API (COMPLETADA)

### Autenticacion
- JWT: POST `/api/auth/login/` y `/api/auth/refresh/`
- Perfil actual: GET/PUT `/api/accounts/me/`
- Cambio de contrasena: POST `/api/accounts/cambiar-password/`

### Roles y permisos (apps/accounts)
- `permissions.py`: `rol_de()`, `EsGerenteRRHH`, `OperarPersonal`, `SoloLectura`
- Roles: Gerente RRHH (total), Administrativo RRHH (alta/modificacion, sin borrar), Solo lectura
- Grupos Django autoasignados al crear usuario segun rol
- API usuarios: `/api/accounts/usuarios/` (solo Gerente)
- API grupos: `/api/accounts/grupos/` (solo Gerente)

### Auditoria (apps/auditoria)
- `middleware.py`: expone el request/usuario al hilo
- `signals.py`: registra CREATE/UPDATE/DELETE de modelos clave en `RegistroAuditoria`
- API solo lectura: `/api/auditoria/registros/` (solo Gerente)
- Registros no eliminables

---

## Endpoints por modulo (API REST)

| Modulo | Base URL |
|---|---|
| Accounts | `/api/accounts/` (usuarios, grupos, me, cambiar-password) |
| Organizacion | `/api/organizacion/unidades/` (+ `/organigrama/`) |
| Puestos | `/api/puestos/puestos/` (+ `/planta_funcional/`) |
| Designaciones | `/api/puestos/designaciones/` |
| Empleados | `/api/empleados/empleados/` (+ `/legajo/`, `/con_documentacion_vencida/`) |
| Categorias doc | `/api/empleados/categorias-documento/` |
| Documentos legajo | `/api/empleados/documentos/` |
| Historial laboral | `/api/empleados/historial/` (sin DELETE) |
| Asistencia | `/api/asistencia/registros/` (+ `/resumen/`) |
| Licencias | `/api/licencias/tipos/`, `/saldos/`, `/solicitudes/` (+ `/aprobar/`, `/rechazar/`) |
| Evaluaciones | `/api/evaluaciones/periodos/`, `/criterios/`, `/evaluaciones/` |
| Sanciones | `/api/sanciones/sanciones/` |
| Incidencias | `/api/incidencias/incidencias/` (+ `/comentar/`, `/cambiar_estado/`, `/reasignar/`) |
| Auditoria | `/api/auditoria/registros/` |
| Docs API | `/api/docs/` (Swagger), `/api/redoc/` |

---

## Verificacion (Fase 2)

- [x] `python manage.py check` -> sin errores
- [x] Schema OpenAPI sin warnings ni errores (drf-spectacular)
- [x] `python manage.py test apps.accounts` -> **3 tests OK**
  - test_perfil_actual, test_flujo_completo, test_login_invalido
- [x] Flujo end-to-end probado: login JWT -> crear unidad, empleado, puesto,
      designacion, asistencia, incidencia -> organigrama, planta funcional, auditoria

---

## Como retomar

```powershell
cd "c:\Users\Usuario\Desktop\Gestion de Recursos Humanos"
.\venv\Scripts\Activate.ps1
python manage.py check
python manage.py runserver
```

| URL | Uso |
|-----|-----|
| http://127.0.0.1:8000/admin/ | Admin (admin / admin123) |
| http://127.0.0.1:8000/api/docs/ | Swagger |
| http://127.0.0.1:8000/api/auth/login/ | JWT login |

### Sesion 3 – 2022-07-10
- Fase 6: reportes PDF (reportlab) y Excel (openpyxl) + informe de promociones potenciales.
- Endpoints: /api/reportes/ (resumen, nomina, cargos-vacantes, ausentismo,
  vacaciones-pendientes, documentacion-vencida, incidencias, sanciones,
  promociones-potenciales). Cada uno con ?formato=json|excel|pdf.
- Tests reportes OK (5/5). Suite total: 8/8 OK. Schema limpio.
- Tests reportes OK (5/5). Suite total: 8/8 OK. Schema limpio.

### Sesion 4 – 2022-07-10 (dashboard + arranque automatico)
- Frontend dashboard web (Django templates + Bootstrap 5 + Chart.js, todo local).
- Superadmin y usuarios hardcodeados (admin/gerente/rrhh/consulta) auto-creados al migrar (post_migrate).
- Scripts de arranque: iniciar.bat / iniciar.ps1 (crea venv, instala, migra, abre el navegador).
- Datos de demo: `python manage.py cargar_demo`.
- Vistas web: login, panel con KPIs + graficos, listados + alta por modulo, detalle de incidencias, reportes (JSON/Excel/PDF).
- Verificado en vivo: login OK, dashboard 200, modulo empleados 200, reportes 200.
- SQLite por defecto (la BD se genera sola). MySQL documentado como opcion.

### Sesion 5 – 2022-07-10 (modulo Usuarios y Roles)
- Agregado modulo "Usuarios y Roles" al dashboard web (visible solo para rol Gerente).
- Funciones: listar, crear, editar (rol / activo / contrasena) y eliminar usuarios desde la web.
- Asignacion automatica de grupo segun el rol elegido.
- Protecciones: no se puede eliminar el propio usuario ni a un superusuario.
- Nota: los usuarios de arranque (admin/gerente/rrhh/consulta) se recrean al ejecutar el sistema.
- Verificado en vivo: listar 200, crear usuario OK y aparece en la lista.

### Sesion 6 – 2022-07-10 (rol Gerente -> "Gerente General")
- El rol de maximo nivel ahora se muestra como "Gerente General" en la interfaz.
- Cambio de solo etiqueta: el codigo interno del rol sigue siendo 'GERENTE' (sin cambios funcionales).
- Archivos: bootstrap, serializers (MAPA_ROL_GRUPO), permissions (docstrings), models (PerfilUsuario),
  forms_usuarios (opciones), cargar_datos_iniciales, login.html.
- Grupo renombrado en la BD (migracion accounts.0002_alter_perfilusuario_rol).
- Verificado en vivo: login y pagina de Usuarios muestran "Gerente General".
- Se elimino el usuario "gerente" (duplicado). Queda UN solo Gerente General: "admin"
  (superusuario, no eliminable). Usuarios finales de arranque: admin, rrhh, consulta.

### Sesion 7 – 2022-07-10 (editar y eliminar en los modulos)
- Los modulos del dashboard ahora permiten EDITAR y ELIMINAR registros (antes solo "Nuevo").
- Columna "Acciones" con botones Editar y Eliminar en cada fila de la tabla.
- Editar: pantalla con el formulario precargado. Eliminar: con confirmacion.
- Permisos: Gerente General y Administrativo pueden operar; "Solo lectura" no ve botones ni puede operar.
- Modelos protegidos (ej. historial laboral) avisan si no se pueden eliminar por datos relacionados.
- Vistas nuevas: modulo_editar, modulo_eliminar. Plantilla: modulo_editar.html.
- Verificado: editar 302 (nombre cambiado), eliminar 302 (registro borrado).


- Listo para empaquetar (.zip) y exponer en feria.

- Pendiente Fase 7: tests formales adicionales y documentacion final.


Ejemplo login (PowerShell):
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"
```

---

## Proximo paso (Fase 6)

1. `apps/reportes`: endpoints de reportes (PDF con reportlab / Excel con openpyxl):
   nomina activa, cargos ocupados/vacantes, movimientos, ausentismo,
   vacaciones pendientes, licencias, documentacion vencida, evaluaciones,
   sanciones, incidencias.
2. Informe de **promociones potenciales** (formacion, experiencia, antiguedad,
   desempeno, competencias).
3. Filtros por trabajador, periodo, cargo, area, estado, tipo de novedad.
4. Actualizar este AVANCES.md.

---

## Registro de sesiones

### Sesion 1 – 2022-07-10
- Fase 0: setup. Fase 1: modelos + migraciones + seeds.

### Sesion 2 – 2022-07-10
- Fase 2: seguridad (JWT, roles, permisos), auditoria (middleware + signals).
- Fases 3-5: API REST completa de todos los modulos (serializers + viewsets + routers).
- Tests funcionales OK (3/3). Schema OpenAPI limpio.
