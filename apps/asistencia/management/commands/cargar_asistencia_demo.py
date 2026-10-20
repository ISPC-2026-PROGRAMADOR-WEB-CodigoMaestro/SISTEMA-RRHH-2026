"""Crea datos de demostración para jornadas y marcaciones."""
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.empleados.models import Empleado

from apps.asistencia.models import AsignacionJornada, Jornada, Marcacion
from apps.asistencia.services import cerrar_dia


class Command(BaseCommand):
    help = 'Crea una jornada predeterminada y marcaciones de demostración idempotentes.'

    @transaction.atomic
    def handle(self, *args, **options):
        jornada = Jornada.objects.filter(
            empleado__isnull=True,
            es_predeterminada=True,
        ).first()
        if jornada is None:
            jornada, _ = Jornada.objects.get_or_create(
                nombre='Jornada predeterminada',
                empleado__isnull=True,
                defaults={
                    'hora_entrada': time(9),
                    'hora_salida': time(18),
                    'tolerancia_minutos': 10,
                    'dias_laborables': '0,1,2,3,4',
                    'es_predeterminada': True,
                    'activa': True,
                },
            )
        jornada.nombre = 'Jornada predeterminada'
        jornada.hora_entrada = time(9)
        jornada.hora_salida = time(18)
        jornada.tolerancia_minutos = 10
        jornada.dias_laborables = '0,1,2,3,4'
        jornada.es_predeterminada = True
        jornada.activa = True
        jornada.save()

        empleados = list(
            Empleado.objects.filter(estado=Empleado.Estado.ACTIVO).order_by('pk')
        )
        for empleado in empleados:
            AsignacionJornada.objects.update_or_create(
                empleado=empleado,
                defaults={'jornada': jornada},
            )

        usuario_rrhh = get_user_model().objects.filter(username='rrhh').first()
        empleado_sin_usuario = next(
            (empleado for empleado in empleados if empleado.usuario_id is None),
            None,
        )
        if (
            usuario_rrhh
            and empleado_sin_usuario
            and not Empleado.objects.filter(usuario=usuario_rrhh).exists()
        ):
            empleado_sin_usuario.usuario = usuario_rrhh
            empleado_sin_usuario.save(update_fields=['usuario'])

        fechas = []
        dia = timezone.localdate() - timedelta(days=1)
        while len(fechas) < 10:
            if dia.weekday() < 5:
                fechas.append(dia)
            dia -= timedelta(days=1)
        fechas.reverse()

        for indice_empleado, empleado in enumerate(empleados):
            for indice_dia, fecha in enumerate(fechas):
                if indice_empleado % 4 == 0 and indice_dia == 4:
                    continue
                tardanza = 15 if indice_dia == 1 else 0
                salida = time(17, 30) if indice_dia == 2 else (
                    time(18, 30) if indice_dia == 3 else time(18)
                )
                entrada_hora = time(9, tardanza)
                for hora, tipo in (
                    (entrada_hora, Marcacion.Tipo.ENTRADA),
                    (salida, Marcacion.Tipo.SALIDA),
                ):
                    naive = datetime.combine(fecha, hora)
                    momento = timezone.make_aware(
                        naive,
                        timezone.get_current_timezone(),
                    )
                    Marcacion.objects.get_or_create(
                        empleado=empleado,
                        fecha_hora=momento,
                        defaults={
                            'tipo': tipo,
                            'origen': Marcacion.Origen.IMPORTACION,
                        },
                    )

        for fecha in fechas:
            cerrar_dia(fecha)
        self.stdout.write(self.style.SUCCESS(
            f'Demo lista: {len(empleados)} empleados, {len(fechas)} días hábiles.'
        ))
