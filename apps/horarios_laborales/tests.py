from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PerfilUsuario
from apps.empleados.models import Empleado
from apps.asistencia.models import RegistroAsistencia

from .models import HorarioDiario, HorarioPredeterminado


class HorarioDiarioApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username='horario-empleado',
            password='test-password',
        )
        self.empleado = self.crear_empleado('H-100', 'H-100', self.user)
        self.otro_empleado = self.crear_empleado('H-200', 'H-200')
        self.horario_propio = HorarioDiario.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 21),
            hora_entrada=time(9),
            hora_salida=time(18),
        )
        self.horario_ajeno = HorarioDiario.objects.create(
            empleado=self.otro_empleado,
            fecha=date(2026, 10, 21),
            hora_entrada=time(10),
            hora_salida=time(19),
        )
        self.registro_propio = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 21),
            hora_ingreso=time(9),
        )
        self.registro_ajeno = RegistroAsistencia.objects.create(
            empleado=self.otro_empleado,
            fecha=date(2026, 10, 21),
            hora_ingreso=time(10),
        )

    def crear_empleado(self, legajo, documento, usuario=None):
        return Empleado.objects.create(
            legajo=legajo,
            numero_documento=documento,
            apellido='Prueba',
            nombre=legajo,
            fecha_ingreso=date(2020, 1, 1),
            usuario=usuario,
        )

    def test_usuario_empleado_solo_lista_sus_horarios(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/asistencia/horarios-diarios/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.horario_propio.pk)

    def test_usuario_empleado_no_puede_editar_horario(self):
        self.client.force_authenticate(self.user)

        response = self.client.patch(
            f'/api/asistencia/horarios-diarios/{self.horario_propio.pk}/',
            {'hora_salida': '20:00'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    def test_administrativo_crea_horario_y_registra_creador(self):
        rrhh = get_user_model().objects.create_user(
            username='horario-rrhh',
            password='test-password',
        )
        PerfilUsuario.objects.create(
            usuario=rrhh,
            rol=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
        )
        self.client.force_authenticate(rrhh)

        response = self.client.post(
            '/api/asistencia/horarios-diarios/',
            {
                'empleado': self.otro_empleado.pk,
                'fecha': '2026-10-22',
                'hora_entrada': '09:00',
                'hora_salida': '18:00',
                'es_franco': False,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        horario = HorarioDiario.objects.get(pk=response.data['id'])
        self.assertEqual(horario.creado_por, rrhh)
        predeterminado = HorarioPredeterminado.objects.get(
            empleado=self.otro_empleado,
        )
        self.assertEqual(predeterminado.vigente_desde, date(2026, 10, 22))

    def test_filtros_fecha_desde_y_hasta(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(
            '/api/asistencia/horarios-diarios/',
            {'fecha_desde': '2026-10-21', 'fecha_hasta': '2026-10-21'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.horario_propio.pk)

    def test_usuario_empleado_solo_lista_sus_registros_de_asistencia(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/asistencia/registros/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.registro_propio.pk)

    def test_rrhh_conserva_lectura_de_todos_los_registros(self):
        rrhh = get_user_model().objects.create_user(
            username='asistencia-rrhh',
            password='test-password',
        )
        PerfilUsuario.objects.create(
            usuario=rrhh,
            rol=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
        )
        self.client.force_authenticate(rrhh)

        response = self.client.get('/api/asistencia/registros/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_api_de_asistencia_devuelve_calculos_solo_lectura(self):
        rrhh = get_user_model().objects.create_user(
            username='asistencia-api-rrhh',
            password='test-password',
        )
        PerfilUsuario.objects.create(
            usuario=rrhh,
            rol=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
        )
        self.client.force_authenticate(rrhh)

        response = self.client.post(
            '/api/asistencia/registros/',
            {
                'empleado': self.otro_empleado.pk,
                'fecha': '2026-10-22',
                'hora_ingreso': '09:00',
                'hora_egreso': '18:00',
                'estado': 'TARDE',
                'minutos_tardanza': 99,
                'minutos_extra': 88,
                'horario_diario': self.horario_ajeno.pk,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['estado'], 'SIN_HORARIO')
        self.assertEqual(response.data['minutos_tardanza'], 0)
        self.assertEqual(response.data['minutos_extra'], 0)
        self.assertIsNone(response.data['horario_diario'])
        self.assertIsNone(response.data['horario_esperado'])
