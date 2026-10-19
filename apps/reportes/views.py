"""Reportes e informes de RRHH (JSON, PDF y Excel)."""
from datetime import date

from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empleados.models import DocumentoLegajo, Empleado, HistorialLaboral
from apps.evaluaciones.models import EvaluacionDesempeno
from apps.incidencias.models import Incidencia
from apps.licencias.models import SaldoVacaciones
from apps.puestos.models import Puesto
from apps.sanciones.models import Sancion

from drf_spectacular.utils import OpenApiTypes, extend_schema

from .utils import generar_excel, generar_pdf


class ReporteBase(APIView):
    """Base para reportes. Soporta formato=json|excel|pdf."""

    permission_classes = [IsAuthenticated]
    titulo = 'Reporte'
    slug = 'reporte'
    columnas = []

    def get_subtitulo(self, request):
        return f'Generado: {timezone.localtime():%Y-%m-%d %H:%M}'

    def get_filas(self, request):
        raise NotImplementedError

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        filas = self.get_filas(request)
        formato = request.query_params.get('formato', 'json').lower()

        if formato == 'pdf':
            contenido = generar_pdf(
                self.titulo, self.columnas, filas, self.get_subtitulo(request)
            )
            resp = HttpResponse(contenido, content_type='application/pdf')
            resp['Content-Disposition'] = f'attachment; filename="{self.slug}.pdf"'
            return resp

        if formato == 'excel':
            contenido = generar_excel(self.titulo, self.columnas, filas)
            resp = HttpResponse(
                contenido,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            resp['Content-Disposition'] = f'attachment; filename="{self.slug}.xlsx"'
            return resp

        return Response({
            'reporte': self.titulo,
            'columnas': self.columnas,
            'total': len(filas),
            'filas': [dict(zip(self.columnas, fila)) for fila in filas],
        })


class ReporteNomina(ReporteBase):
    titulo = 'Nomina de Personal Activo'
    slug = 'nomina'
    columnas = ['Legajo', 'Apellido', 'Nombre', 'Documento', 'Unidad', 'Estado', 'Ingreso']

    def get_filas(self, request):
        qs = Empleado.objects.select_related('unidad')
        estado = request.query_params.get('estado', 'ACTIVO')
        qs = qs.filter(estado=estado)
        unidad = request.query_params.get('unidad')
        if unidad:
            qs = qs.filter(unidad_id=unidad)
        return [
            [e.legajo, e.apellido, e.nombre, e.numero_documento,
             e.unidad.nombre if e.unidad else '', e.get_estado_display(), e.fecha_ingreso]
            for e in qs.order_by('apellido', 'nombre')
        ]


class ReporteCargosVacantes(ReporteBase):
    titulo = 'Cargos Ocupados y Vacantes'
    slug = 'cargos-vacantes'
    columnas = ['Codigo', 'Puesto', 'Unidad', 'Previstos', 'Ocupados', 'Vacantes']

    def get_filas(self, request):
        qs = Puesto.objects.filter(activo=True).select_related('unidad')
        unidad = request.query_params.get('unidad')
        if unidad:
            qs = qs.filter(unidad_id=unidad)
        return [
            [p.codigo, p.denominacion, p.unidad.nombre if p.unidad else '',
             p.cantidad_prevista, p.cantidad_ocupados, p.cantidad_vacantes]
            for p in qs.order_by('unidad__nombre', 'denominacion')
        ]


class ReporteAusentismo(ReporteBase):
    titulo = 'Reporte de Ausentismo'
    slug = 'ausentismo'
    columnas = ['Legajo', 'Apellido', 'Nombre', 'Registros', 'Ausencias', 'Tardanzas', 'Min. Tardanza']

    def get_filas(self, request):
        from apps.asistencia.models import RegistroAsistencia
        qs = RegistroAsistencia.objects.all()
        desde = request.query_params.get('desde')
        hasta = request.query_params.get('hasta')
        if desde:
            qs = qs.filter(fecha__gte=desde)
        if hasta:
            qs = qs.filter(fecha__lte=hasta)
        resumen = (
            qs.values('empleado__legajo', 'empleado__apellido', 'empleado__nombre')
            .annotate(
                total=Count('id'),
                ausencias=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.AUSENTE)),
                tardanzas=Count('id', filter=Q(tipo=RegistroAsistencia.Tipo.TARDANZA)),
                minutos=Sum('minutos_tardanza'),
            )
            .order_by('empleado__apellido')
        )
        return [
            [r['empleado__legajo'], r['empleado__apellido'], r['empleado__nombre'],
             r['total'], r['ausencias'], r['tardanzas'], r['minutos'] or 0]
            for r in resumen
        ]


class ReporteVacacionesPendientes(ReporteBase):
    titulo = 'Vacaciones Pendientes'
    slug = 'vacaciones-pendientes'
    columnas = ['Legajo', 'Apellido', 'Nombre', 'Anio', 'Correspondientes', 'Usados', 'Pendientes']

    def get_filas(self, request):
        qs = SaldoVacaciones.objects.select_related('empleado').filter(dias_pendientes__gt=0)
        anio = request.query_params.get('anio')
        if anio:
            qs = qs.filter(anio=anio)
        return [
            [s.empleado.legajo, s.empleado.apellido, s.empleado.nombre, s.anio,
             s.dias_correspondientes, s.dias_usados, s.dias_pendientes]
            for s in qs.order_by('empleado__apellido')
        ]


class ReporteDocumentacionVencida(ReporteBase):
    titulo = 'Documentacion Vencida o por Vencer'
    slug = 'documentacion-vencida'
    columnas = ['Legajo', 'Apellido', 'Categoria', 'Documento', 'Vencimiento', 'Estado']

    def get_filas(self, request):
        hoy = timezone.localdate()
        qs = DocumentoLegajo.objects.filter(
            activo=True, fecha_vencimiento__isnull=False
        ).select_related('empleado', 'categoria')
        filas = []
        for d in qs.order_by('fecha_vencimiento'):
            estado = 'VENCIDO' if d.fecha_vencimiento < hoy else 'POR VENCER'
            filas.append([
                d.empleado.legajo, d.empleado.apellido, d.categoria.nombre,
                d.titulo, d.fecha_vencimiento, estado,
            ])
        return filas


class ReporteIncidencias(ReporteBase):
    titulo = 'Reporte de Incidencias'
    slug = 'incidencias'
    columnas = ['Numero', 'Fecha', 'Categoria', 'Titulo', 'Prioridad', 'Estado', 'Responsable']

    def get_filas(self, request):
        qs = Incidencia.objects.select_related('responsable')
        estado = request.query_params.get('estado')
        prioridad = request.query_params.get('prioridad')
        if estado:
            qs = qs.filter(estado=estado)
        if prioridad:
            qs = qs.filter(prioridad=prioridad)
        return [
            [i.numero, i.fecha_creacion.date(), i.get_categoria_display(), i.titulo,
             i.get_prioridad_display(), i.get_estado_display(),
             str(i.responsable) if i.responsable else '']
            for i in qs.order_by('-fecha_creacion')
        ]


class ReporteSanciones(ReporteBase):
    titulo = 'Reporte de Sanciones'
    slug = 'sanciones'
    columnas = ['Legajo', 'Apellido', 'Nombre', 'Fecha hecho', 'Tipo', 'Estado']

    def get_filas(self, request):
        qs = Sancion.objects.select_related('empleado')
        return [
            [s.empleado.legajo, s.empleado.apellido, s.empleado.nombre,
             s.fecha_hecho, s.get_tipo_display(), s.get_estado_display()]
            for s in qs.order_by('-fecha_hecho')
        ]


class ReportePromocionesPotenciales(ReporteBase):
    """Candidatos a promocion segun antiguedad, desempeno y capacitacion."""

    titulo = 'Informe de Promociones Potenciales'
    slug = 'promociones-potenciales'
    columnas = ['Legajo', 'Apellido', 'Nombre', 'Antiguedad (anios)',
                'Desempeno prom.', 'Capacitaciones', 'Puntaje', 'Recomendacion']

    def get_filas(self, request):
        hoy = date.today()
        empleados = Empleado.objects.filter(
            estado='ACTIVO'
        ).prefetch_related('evaluaciones', 'historial')
        filas = []
        for e in empleados:
            antiguedad = 0.0
            if e.fecha_ingreso:
                antiguedad = (hoy - e.fecha_ingreso).days / 365.25

            prom = e.evaluaciones.aggregate(p=Avg('calificacion_general'))['p'] or 0

            capacitaciones = e.historial.filter(
                tipo_movimiento=HistorialLaboral.TipoMovimiento.CAPACITACION
            ).count()

            puntaje = round(min(antiguedad, 20) * 1.0 + float(prom) * 5.0 + capacitaciones * 2.0, 2)
            if puntaje >= 45:
                recomendacion = 'Alta'
            elif puntaje >= 25:
                recomendacion = 'Media'
            else:
                recomendacion = 'Baja'

            filas.append([
                e.legajo, e.apellido, e.nombre, round(antiguedad, 1),
                round(float(prom), 2), capacitaciones, puntaje, recomendacion,
            ])
        filas.sort(key=lambda f: f[6], reverse=True)
        return filas


class ResumenGeneral(APIView):
    """KPIs generales del sistema (para dashboard)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        hoy = timezone.localdate()
        data = {
            'empleados_activos': Empleado.objects.filter(estado='ACTIVO').count(),
            'empleados_total': Empleado.objects.count(),
            'cargos_previstos': Puesto.objects.filter(activo=True).aggregate(
                t=Sum('cantidad_prevista')
            )['t'] or 0,
            'incidencias_abiertas': Incidencia.objects.exclude(
                estado__in=[Incidencia.Estado.RESUELTA, Incidencia.Estado.CERRADA]
            ).count(),
            'documentos_vencidos': DocumentoLegajo.objects.filter(
                activo=True, fecha_vencimiento__lt=hoy
            ).count(),
            'sanciones_total': Sancion.objects.count(),
            'evaluaciones_total': EvaluacionDesempeno.objects.count(),
        }
        return Response(data)


