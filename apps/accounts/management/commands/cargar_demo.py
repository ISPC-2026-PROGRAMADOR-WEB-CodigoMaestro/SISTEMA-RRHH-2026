"""Carga datos de demostración (opcional) para poblar el sistema."""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.asistencia.models import RegistroAsistencia
from apps.empleados.models import Empleado
from apps.incidencias.models import Incidencia
from apps.licencias.models import SaldoVacaciones, TipoLicencia
from apps.organizacion.models import UnidadOrganizacional
from apps.puestos.models import Designacion, Puesto
from apps.sanciones.models import Sancion


class Command(BaseCommand):
    help = 'Carga datos de demostración (unidades, empleados, puestos, etc.)'

    def handle(self, *args, **options):
        self._unidades()
        self._empleados()
        self._puestos_y_designaciones()
        self._asistencia()
        self._incidencias()
        self._sanciones()
        self._vacaciones()
        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))

    def _unidades(self):
        gg, _ = UnidadOrganizacional.objects.get_or_create(
            codigo='GG', defaults={'nombre': 'Gerencia General', 'tipo': 'GERENCIA', 'orden': 1})
        rrhh, _ = UnidadOrganizacional.objects.get_or_create(
            codigo='RRHH', defaults={'nombre': 'Recursos Humanos', 'tipo': 'AREA', 'parent': gg, 'orden': 2})
        adm, _ = UnidadOrganizacional.objects.get_or_create(
            codigo='ADM', defaults={'nombre': 'Administración', 'tipo': 'AREA', 'parent': gg, 'orden': 3})
        sis, _ = UnidadOrganizacional.objects.get_or_create(
            codigo='SIS', defaults={'nombre': 'Sistemas', 'tipo': 'DEPARTAMENTO', 'parent': gg, 'orden': 4})
        self._unidades_map = {'GG': gg, 'RRHH': rrhh, 'ADM': adm, 'SIS': sis}

    def _empleados(self):
        datos = [
            ('0001', 'Gómez', 'Gabriela', 'F', 'RRHH', '2020-03-01', 'GERENTE'),
            ('0002', 'Rodríguez', 'Ramiro', 'M', 'RRHH', '2021-06-15', 'ADMINISTRATIVO'),
            ('0003', 'Fernández', 'Carla', 'F', 'ADM', '2019-01-10', 'ADMINISTRATIVO'),
            ('0004', 'López', 'Lucas', 'M', 'SIS', '2022-08-20', 'ANALISTA'),
            ('0005', 'Martínez', 'Sofía', 'F', 'SIS', '2023-02-05', 'ANALISTA'),
        ]
        self._empleados_map = {}
        for legajo, ap, nom, gen, uni, ingreso, _ in datos:
            emp, _c = Empleado.objects.get_or_create(
                legajo=legajo,
                defaults={
                    'tipo_documento': 'DNI',
                    'numero_documento': f'30{legajo}0000',
                    'apellido': ap, 'nombre': nom, 'genero': gen,
                    'fecha_ingreso': ingreso, 'estado': 'ACTIVO',
                    'unidad': self._unidades_map.get(uni),
                    'email': f'{nom.lower()}@rrhh.local',
                },
            )
            self._empleados_map[legajo] = emp

    def _puestos_y_designaciones(self):
        puestos = [
            ('P-001', 'Gerente de RRHH', 'RRHH', 'GERENCIA', 1),
            ('P-002', 'Analista de RRHH', 'RRHH', 'OPERATIVO', 2),
            ('P-003', 'Administrativo', 'ADM', 'OPERATIVO', 2),
            ('P-004', 'Analista de Sistemas', 'SIS', 'OPERATIVO', 3),
        ]
        self._puestos_map = {}
        for cod, den, uni, nivel, prev in puestos:
            p, _ = Puesto.objects.get_or_create(
                codigo=cod,
                defaults={
                    'denominacion': den,
                    'unidad': self._unidades_map[uni],
                    'nivel_autoridad': nivel,
                    'cantidad_prevista': prev,
                },
            )
            self._puestos_map[cod] = p
        asignaciones = [
            ('0001', 'P-001'), ('0002', 'P-002'), ('0003', 'P-003'),
            ('0004', 'P-004'), ('0005', 'P-004'),
        ]
        for legajo, cod in asignaciones:
            emp = self._empleados_map[legajo]
            Designacion.objects.get_or_create(
                empleado=emp, puesto=self._puestos_map[cod],
                defaults={'fecha_inicio': emp.fecha_ingreso, 'activa': True},
            )

    def _asistencia(self):
        hoy = date.today()
        for legajo, emp in self._empleados_map.items():
            for i in range(5):
                RegistroAsistencia.objects.get_or_create(
                    empleado=emp, fecha=hoy - timedelta(days=i),
                    defaults={'tipo': 'PRESENTE'},
                )

    def _incidencias(self):
        ejemplos = [
            ('0003', 'DOCUMENTACION', 'Falta certificado médico', 'MEDIA'),
            ('0005', 'ASISTENCIA', 'Tardanza reiterada', 'ALTA'),
            ('0004', 'ADMINISTRATIVO', 'Error en liquidación de haberes', 'CRITICA'),
        ]
        for legajo, cat, titulo, prio in ejemplos:
            Incidencia.objects.get_or_create(
                titulo=titulo,
                defaults={
                    'empleado': self._empleados_map[legajo],
                    'categoria': cat, 'descripcion': titulo,
                    'prioridad': prio, 'estado': 'ABIERTA',
                },
            )

    def _sanciones(self):
        Sancion.objects.get_or_create(
            empleado=self._empleados_map['0005'],
            fecha_hecho=date.today() - timedelta(days=10),
            tipo='LLAMADO',
            defaults={'descripcion': 'Llamado de atención por impuntualidad',
                      'medida_adoptada': 'Apercibimiento verbal', 'estado': 'NOTIFICADA'},
        )

    def _vacaciones(self):
        anio = date.today().year
        for legajo, emp in self._empleados_map.items():
            SaldoVacaciones.objects.get_or_create(
                empleado=emp, anio=anio,
                defaults={'dias_correspondientes': 14, 'dias_usados': 4, 'dias_pendientes': 10},
            )
