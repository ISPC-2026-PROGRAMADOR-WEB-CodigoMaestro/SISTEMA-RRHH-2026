"""Cierra y consolida uno o varios días de asistencia."""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.asistencia.services import cerrar_dia


class Command(BaseCommand):
    help = (
        'Consolida marcaciones y genera registros de licencias, vacaciones y ausencias '
        'para la fecha indicada.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--fecha', help='Fecha única con formato YYYY-MM-DD.')
        parser.add_argument('--desde', help='Inicio inclusivo del rango YYYY-MM-DD.')
        parser.add_argument('--hasta', help='Fin inclusivo del rango YYYY-MM-DD.')

    def handle(self, *args, **options):
        desde = options['desde']
        hasta = options['hasta']
        if bool(desde) != bool(hasta):
            raise CommandError('Debes indicar --desde y --hasta juntos.')
        if desde and options['fecha']:
            raise CommandError('Usa --fecha o el rango --desde/--hasta, no ambos.')
        try:
            if desde:
                primera = date.fromisoformat(desde)
                ultima = date.fromisoformat(hasta)
            else:
                primera = ultima = (
                    date.fromisoformat(options['fecha'])
                    if options['fecha']
                    else timezone.localdate() - timedelta(days=1)
                )
        except ValueError as exc:
            raise CommandError('Las fechas deben tener formato YYYY-MM-DD.') from exc
        if ultima < primera:
            raise CommandError('--hasta no puede ser anterior a --desde.')

        actual = primera
        while actual <= ultima:
            resumen = cerrar_dia(actual)
            self.stdout.write(
                f'{actual}: consolidados={resumen["consolidados"]}, '
                f'ausentes_creados={resumen["ausentes_creados"]}, '
                f'licencias_creadas={resumen["licencias_creadas"]}, '
                f'omitidos={resumen["omitidos"]}'
            )
            actual += timedelta(days=1)
