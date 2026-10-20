"""Carga datos iniciales: grupos/roles, categorias de documento y tipos de licencia."""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.empleados.models import CategoriaDocumento
from apps.evaluaciones.models import CriterioEvaluacion
from apps.licencias.models import TipoLicencia


class Command(BaseCommand):
    help = 'Carga datos iniciales del sistema de RRHH'

    def handle(self, *args, **options):
        self._grupos()
        self._categorias_documento()
        self._tipos_licencia()
        self._criterios_evaluacion()
        self.stdout.write(self.style.SUCCESS('Datos iniciales cargados correctamente.'))

    def _grupos(self):
        roles = [
            'Gerente General',
            'Administrativo de Recursos Humanos',
            'Solo lectura',
        ]
        for nombre in roles:
            group, created = Group.objects.get_or_create(name=nombre)
            if created:
                self.stdout.write(f'  Grupo creado: {nombre}')
            # Gerente: todos los permisos
            if nombre == 'Gerente General':
                group.permissions.set(Permission.objects.all())
            # Administrativo: add/change/view (sin delete ni auth)
            elif nombre == 'Administrativo de Recursos Humanos':
                perms = Permission.objects.exclude(
                    content_type__app_label__in=['auth', 'admin', 'sessions', 'contenttypes']
                ).exclude(codename__startswith='delete_')
                group.permissions.set(perms)
            # Solo lectura: solo view
            else:
                perms = Permission.objects.filter(codename__startswith='view_')
                group.permissions.set(perms)

    def _categorias_documento(self):
        cats = [
            ('Contrato', True, 30, True),
            ('DNI / Identificacion', False, 0, True),
            ('CUIL', False, 0, True),
            ('Titulo / Certificacion', False, 0, False),
            ('Matricula profesional', True, 60, False),
            ('Examen medico', True, 30, True),
            ('Constancia', False, 0, False),
            ('Recibo de sueldo', False, 0, True),
            ('Notificacion', False, 0, False),
            ('Licencia / Certificado', True, 15, True),
            ('Sancion', False, 0, True),
            ('Otro', False, 0, False),
        ]
        for nombre, vence, dias, sensible in cats:
            obj, created = CategoriaDocumento.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'requiere_vencimiento': vence,
                    'dias_alerta_previa': dias,
                    'sensible': sensible,
                },
            )
            if created:
                self.stdout.write(f'  Categoria documento: {nombre}')

    def _tipos_licencia(self):
        tipos = [
            ('VAC', 'Vacaciones', None, True, True),
            ('ENF', 'Licencia por enfermedad', None, True, False),
            ('MAT', 'Licencia por maternidad', 90, True, False),
            ('PAT', 'Licencia por paternidad', 15, True, False),
            ('EST', 'Licencia por estudio', 10, True, False),
            ('ACC', 'Licencia por accidente', None, True, False),
            ('PAR', 'Asuntos particulares', 5, True, False),
            ('DOL', 'Duelo', 3, True, False),
        ]
        for codigo, nombre, dias, aprueba, descuenta in tipos:
            obj, created = TipoLicencia.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'dias_maximos': dias,
                    'requiere_aprobacion': aprueba,
                    'descuenta_vacaciones': descuenta,
                },
            )
            if created:
                self.stdout.write(f'  Tipo licencia: {codigo} - {nombre}')

    def _criterios_evaluacion(self):
        criterios = [
            ('Cumplimiento de objetivos', 1.5, 1),
            ('Calidad del trabajo', 1.5, 2),
            ('Productividad', 1.2, 3),
            ('Responsabilidad', 1.2, 4),
            ('Trabajo en equipo', 1.0, 5),
            ('Liderazgo', 1.0, 6),
            ('Competencias tecnicas', 1.3, 7),
            ('Conducta laboral', 1.0, 8),
        ]
        for nombre, peso, orden in criterios:
            obj, created = CriterioEvaluacion.objects.get_or_create(
                nombre=nombre,
                defaults={'peso': peso, 'orden': orden},
            )
            if created:
                self.stdout.write(f'  Criterio evaluacion: {nombre}')
