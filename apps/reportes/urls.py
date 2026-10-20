"""Rutas de la app reportes."""
from django.urls import path

from .views import (
    ReporteAusentismo,
    ReporteCargosVacantes,
    ReporteDocumentacionVencida,
    ReporteIncidencias,
    ReporteNomina,
    ReportePromocionesPotenciales,
    ReporteSanciones,
    ReporteVacacionesPendientes,
    ResumenGeneral,
)

urlpatterns = [
    path('resumen/', ResumenGeneral.as_view(), name='reporte-resumen'),
    path('nomina/', ReporteNomina.as_view(), name='reporte-nomina'),
    path('cargos-vacantes/', ReporteCargosVacantes.as_view(), name='reporte-cargos-vacantes'),
    path('ausentismo/', ReporteAusentismo.as_view(), name='reporte-ausentismo'),
    path('vacaciones-pendientes/', ReporteVacacionesPendientes.as_view(), name='reporte-vacaciones'),
    path('documentacion-vencida/', ReporteDocumentacionVencida.as_view(), name='reporte-doc-vencida'),
    path('incidencias/', ReporteIncidencias.as_view(), name='reporte-incidencias'),
    path('sanciones/', ReporteSanciones.as_view(), name='reporte-sanciones'),
    path('promociones-potenciales/', ReportePromocionesPotenciales.as_view(), name='reporte-promociones'),
]
