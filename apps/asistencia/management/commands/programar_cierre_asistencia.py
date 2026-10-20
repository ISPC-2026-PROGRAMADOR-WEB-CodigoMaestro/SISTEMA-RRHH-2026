"""Programa el cierre diario de asistencia en el Programador de tareas de Windows."""
import os
import subprocess
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Programa el cierre automático diario de asistencia a medianoche en Windows.'

    def handle(self, *args, **options):
        if os.name != 'nt':
            raise CommandError('Este comando solo está disponible en Windows.')

        def powershell_literal(value):
            return "'" + str(value).replace("'", "''") + "'"

        script = '\n'.join((
            f"$python = {powershell_literal(sys.executable)}",
            f"$project = {powershell_literal(settings.BASE_DIR)}",
            "$action = New-ScheduledTaskAction -Execute $python "
            "-Argument '\"manage.py\" cerrar_asistencia' -WorkingDirectory $project",
            "$trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddDays(1))",
            "$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable",
            "$principal = New-ScheduledTaskPrincipal "
            "-UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) "
            "-LogonType Interactive -RunLevel Limited",
            "Register-ScheduledTask -TaskName 'GestionRRHH-CierreAsistencia' "
            "-Action $action -Trigger $trigger -Settings $settings "
            "-Principal $principal -Description "
            "'Cierra asistencia y genera ausencias, licencias y vacaciones' -Force "
            "| Out-Null",
        ))
        try:
            subprocess.run(
                ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise CommandError('No se encontró PowerShell para crear la tarea programada.') from exc
        except subprocess.CalledProcessError as exc:
            detalle = exc.stderr.strip() or exc.stdout.strip() or str(exc)
            raise CommandError(f'No se pudo programar el cierre diario: {detalle}') from exc

        self.stdout.write(self.style.SUCCESS(
            'Cierre automático programado diariamente a las 00:00. '
            'Windows podrá iniciarla al volver a estar disponible si perdió el horario; '
            'deja abierta la sesión de Windows de esta cuenta.'
        ))
