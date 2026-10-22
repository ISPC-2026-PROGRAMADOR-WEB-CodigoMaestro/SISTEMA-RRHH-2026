"""Recalcula métricas de registros de asistencia existentes."""
from copy import copy
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.asistencia.models import RegistroAsistencia
from apps.asistencia.services import calcular_novedades


class Command(BaseCommand):
    help = 'Recalcula estado y métricas de asistencia en un rango de fechas.'

    campos_calculados = (
        'horario_diario_id',
        'estado',
        'tipo',
        'minutos_tardanza',
        'minutos_extra',
    )

    def add_arguments(self, parser):
        parser.add_argument('--desde', required=True, help='Inicio inclusivo YYYY-MM-DD.')
        parser.add_argument('--hasta', required=True, help='Fin inclusivo YYYY-MM-DD.')
        parser.add_argument('--empleado', type=int, help='ID de empleado opcional.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra cuántos registros cambiarían sin guardar cambios.',
        )

    def handle(self, *args, **options):
        try:
            desde = date.fromisoformat(options['desde'])
            hasta = date.fromisoformat(options['hasta'])
        except ValueError as exc:
            raise CommandError('Las fechas deben tener formato YYYY-MM-DD.') from exc
        if hasta < desde:
            raise CommandError('--hasta no puede ser anterior a --desde.')

        registros = RegistroAsistencia.objects.filter(
            fecha__gte=desde,
            fecha__lte=hasta,
        ).select_related('empleado').order_by('fecha', 'empleado_id')
        if options['empleado'] is not None:
            registros = registros.filter(empleado_id=options['empleado'])

        cambiados = 0
        for registro in registros.iterator():
            actual = tuple(getattr(registro, campo) for campo in self.campos_calculados)
            calculado = copy(registro)
            calcular_novedades(calculado)
            resultado = tuple(
                getattr(calculado, campo) for campo in self.campos_calculados
            )
            if resultado == actual:
                continue
            cambiados += 1
            if not options['dry_run']:
                registro.save()

        if options['dry_run']:
            self.stdout.write(f'{cambiados} registros cambiarían; no se guardaron cambios.')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{cambiados} registros recalculados y guardados.'
            ))
