"""Registro central de módulos y utilidades de visualización del dashboard."""
from apps.asistencia.models import RegistroAsistencia
from apps.empleados.models import DocumentoLegajo, Empleado, HistorialLaboral
from apps.evaluaciones.models import EvaluacionDesempeno
from apps.incidencias.models import Incidencia
from apps.licencias.models import SaldoVacaciones, SolicitudLicencia
from apps.organizacion.models import UnidadOrganizacional
from apps.puestos.models import Designacion, Puesto
from apps.sanciones.models import Sancion

from .forms import (
    AsistenciaForm,
    DesignacionForm,
    DocumentoForm,
    EmpleadoForm,
    EvaluacionForm,
    IncidenciaForm,
    PuestoForm,
    SancionForm,
    SolicitudLicenciaForm,
    UnidadForm,
)


def display(obj, attr):
    """Devuelve el valor legible de un atributo (soporta FK, display y booleanos)."""
    if obj is None:
        return ''
    if '.' in attr:
        primero, resto = attr.split('.', 1)
        return display(getattr(obj, primero, None), resto)
    getter = getattr(obj, f'get_{attr}_display', None)
    if callable(getter):
        return getter()
    valor = getattr(obj, attr, '')
    if valor is None:
        return ''
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    return valor


MODULOS = {
    'empleados': {
        'titulo': 'Empleados', 'icono': 'bi-people', 'model': Empleado,
        'form': EmpleadoForm,
        'columnas': [('Legajo', 'legajo'), ('Apellido', 'apellido'), ('Nombre', 'nombre'),
                     ('Documento', 'numero_documento'), ('Estado', 'estado'), ('Unidad', 'unidad.nombre')],
        'search': ['legajo', 'apellido', 'nombre', 'numero_documento'],
    },
    'unidades': {
        'titulo': 'Estructura Organizacional', 'icono': 'bi-diagram-3', 'model': UnidadOrganizacional,
        'form': UnidadForm,
        'columnas': [('Código', 'codigo'), ('Nombre', 'nombre'), ('Tipo', 'tipo'),
                     ('Depende de', 'parent.nombre'), ('Activa', 'activa')],
        'search': ['codigo', 'nombre'],
    },
    'puestos': {
        'titulo': 'Puestos y Cargos', 'icono': 'bi-briefcase', 'model': Puesto,
        'form': PuestoForm,
        'columnas': [('Código', 'codigo'), ('Denominación', 'denominacion'), ('Unidad', 'unidad.nombre'),
                     ('Previstos', 'cantidad_prevista'), ('Vacantes', 'cantidad_vacantes'), ('Activo', 'activo')],
        'search': ['codigo', 'denominacion'],
    },
    'designaciones': {
        'titulo': 'Designaciones', 'icono': 'bi-person-check', 'model': Designacion,
        'form': DesignacionForm,
        'columnas': [('Empleado', 'empleado'), ('Puesto', 'puesto.denominacion'), ('Inicio', 'fecha_inicio'),
                     ('Modalidad', 'modalidad_contractual'), ('Activa', 'activa')],
        'search': ['empleado__apellido', 'empleado__legajo'],
    },
    'documentos': {
        'titulo': 'Legajo Digital', 'icono': 'bi-folder2-open', 'model': DocumentoLegajo,
        'form': DocumentoForm,
        'columnas': [('Empleado', 'empleado'), ('Categoría', 'categoria.nombre'), ('Título', 'titulo'),
                     ('Vencimiento', 'fecha_vencimiento'), ('Vencido', 'esta_vencido')],
        'search': ['titulo', 'empleado__apellido'],
    },
    'asistencia': {
        'titulo': 'Control de Asistencia', 'icono': 'bi-clock-history', 'model': RegistroAsistencia,
        'form': AsistenciaForm,
        'columnas': [('Empleado', 'empleado'), ('Fecha', 'fecha'), ('Tipo', 'tipo'),
                     ('Ingreso', 'hora_ingreso'), ('Egreso', 'hora_egreso'), ('Justificado', 'justificado')],
        'search': ['empleado__apellido', 'empleado__legajo'],
    },
    'licencias': {
        'titulo': 'Vacaciones y Licencias', 'icono': 'bi-calendar-check', 'model': SolicitudLicencia,
        'form': SolicitudLicenciaForm,
        'columnas': [('Empleado', 'empleado'), ('Tipo', 'tipo_licencia.nombre'), ('Desde', 'fecha_inicio'),
                     ('Hasta', 'fecha_fin'), ('Días', 'dias_solicitados'), ('Estado', 'estado')],
        'search': ['empleado__apellido', 'empleado__legajo'],
    },
    'evaluaciones': {
        'titulo': 'Evaluaciones de Desempeño', 'icono': 'bi-clipboard-data', 'model': EvaluacionDesempeno,
        'form': EvaluacionForm,
        'columnas': [('Empleado', 'empleado'), ('Período', 'periodo.nombre'), ('Fecha', 'fecha_evaluacion'),
                     ('Calificación', 'calificacion_general'), ('Estado', 'estado')],
        'search': ['empleado__apellido', 'empleado__legajo'],
    },
    'sanciones': {
        'titulo': 'Sanciones', 'icono': 'bi-exclamation-triangle', 'model': Sancion,
        'form': SancionForm,
        'columnas': [('Empleado', 'empleado'), ('Tipo', 'tipo'), ('Fecha hecho', 'fecha_hecho'),
                     ('Estado', 'estado')],
        'search': ['empleado__apellido', 'empleado__legajo'],
    },
    'incidencias': {
        'titulo': 'Incidencias', 'icono': 'bi-inbox', 'model': Incidencia,
        'form': IncidenciaForm,
        'columnas': [('Número', 'numero'), ('Título', 'titulo'), ('Categoría', 'categoria'),
                     ('Prioridad', 'prioridad'), ('Estado', 'estado'), ('Responsable', 'responsable')],
        'search': ['numero', 'titulo'],
    },
    'historial': {
        'titulo': 'Vida Laboral', 'icono': 'bi-journal-text', 'model': HistorialLaboral,
        'form': None,
        'columnas': [('Empleado', 'empleado'), ('Fecha', 'fecha'), ('Movimiento', 'tipo_movimiento'),
                     ('Descripción', 'descripcion')],
        'search': ['empleado__apellido', 'descripcion'],
    },
}
