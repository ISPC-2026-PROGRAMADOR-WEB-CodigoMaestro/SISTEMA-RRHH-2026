from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.asistencia.models import RegistroAsistencia
from apps.empleados.models import Empleado
from apps.incidencias.models import Incidencia
from apps.licencias.models import SolicitudLicencia, TipoLicencia


class AutoservicioLicenciasTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-dev2-autoservicio',
            password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='WEB-100',
            numero_documento='WEB-100',
            apellido='López',
            nombre='María',
            fecha_ingreso=date(2022, 1, 1),
            usuario=self.user,
        )
        self.tipo = TipoLicencia.objects.create(
            codigo='TEST-WEB',
            nombre='Licencia de prueba',
        )
        self.client.login(username='test-dev2-autoservicio', password='test-password')

    def test_empleado_solicita_licencia_desde_autoservicio(self):
        response = self.client.post('/mis-licencias/', {
            'tipo_licencia': self.tipo.pk,
            'fecha_inicio': '2026-11-09',
            'fecha_fin': '2026-11-10',
            'motivo': 'Trámite personal',
        })

        self.assertRedirects(response, '/mis-licencias/')
        solicitud = SolicitudLicencia.objects.get(empleado=self.empleado)
        self.assertEqual(solicitud.solicitado_por, self.user)
        self.assertEqual(solicitud.dias_solicitados, 2)
        self.assertEqual(solicitud.estado, SolicitudLicencia.Estado.PENDIENTE)

    def test_vincular_usuario_a_empleado_muestra_menu_de_mis_licencias(self):
        usuario = get_user_model().objects.create_user(
            username='test-dev2-vinculo',
            password='test-password',
        )
        administrador = get_user_model().objects.create_superuser(
            username='test-dev2-admin',
            password='test-password',
            email='admin@example.com',
        )
        self.client.force_login(administrador)

        response = self.client.post('/m/empleados/', {
            'legajo': 'WEB-101',
            'tipo_documento': 'DNI',
            'numero_documento': 'WEB-101',
            'apellido': 'García',
            'nombre': 'Juan',
            'fecha_ingreso': '2022-01-01',
            'estado': 'ACTIVO',
            'usuario': usuario.pk,
        })

        self.assertRedirects(response, '/m/empleados/')
        empleado = Empleado.objects.get(legajo='WEB-101')
        self.assertEqual(empleado.usuario, usuario)

        self.client.force_login(usuario)
        response = self.client.get('/')

        self.assertContains(response, 'Mis licencias')


class ListaAsistenciaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='asistencia-lista-admin',
            password='test-password',
            email='asistencia-lista-admin@example.com',
        )
        self.client.force_login(self.user)
        self.empleado = Empleado.objects.create(
            legajo='LISTA-100',
            numero_documento='LISTA-100',
            apellido='Prueba',
            nombre='Asistencia',
            fecha_ingreso=date(2020, 1, 1),
        )

    def test_lista_asistencia_filtra_fecha_y_muestra_registro_generado(self):
        fecha = date(2026, 10, 12)
        RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=fecha,
            tipo=RegistroAsistencia.Tipo.AUSENTE,
        )
        RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 13),
            tipo=RegistroAsistencia.Tipo.LICENCIA,
        )

        response = self.client.get('/m/asistencia/', {'fecha': '2026-10-12'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LISTA-100')
        self.assertContains(response, 'Ausente')
        self.assertContains(response, '2026-10-12')
        self.assertEqual(response.context['total'], 1)
        self.assertContains(
            response,
            f'/asistencia/empleados/{self.empleado.pk}/?mes=2026-10',
        )

    def test_lista_asistencia_muestra_todos_los_empleados_con_sus_licencias(self):
        fecha = date(2026, 10, 12)
        empleado_vacaciones = Empleado.objects.create(
            legajo='LISTA-VAC',
            numero_documento='LISTA-VAC',
            apellido='Vacaciones',
            nombre='Empleado',
            fecha_ingreso=date(2020, 1, 1),
        )
        empleado_licencia = Empleado.objects.create(
            legajo='LISTA-LIC',
            numero_documento='LISTA-LIC',
            apellido='Licencia',
            nombre='Empleado',
            fecha_ingreso=date(2020, 1, 1),
        )
        vacaciones = TipoLicencia.objects.create(
            codigo='LISTA-VAC',
            nombre='Vacaciones',
            descuenta_vacaciones=True,
        )
        licencia = TipoLicencia.objects.create(
            codigo='LISTA-LIC',
            nombre='Licencia médica',
        )
        SolicitudLicencia.objects.create(
            empleado=empleado_vacaciones,
            tipo_licencia=vacaciones,
            fecha_inicio=fecha,
            fecha_fin=fecha,
            dias_solicitados=1,
            estado=SolicitudLicencia.Estado.PENDIENTE,
        )
        SolicitudLicencia.objects.create(
            empleado=empleado_licencia,
            tipo_licencia=licencia,
            fecha_inicio=fecha,
            fecha_fin=fecha,
            dias_solicitados=1,
            estado=SolicitudLicencia.Estado.RECHAZADA,
        )
        RegistroAsistencia.objects.create(
            empleado=empleado_vacaciones,
            fecha=fecha,
            tipo=RegistroAsistencia.Tipo.AUSENTE,
        )
        RegistroAsistencia.objects.create(
            empleado=empleado_licencia,
            fecha=fecha,
            tipo=RegistroAsistencia.Tipo.AUSENTE,
        )

        response = self.client.get('/m/asistencia/', {'fecha': '2026-10-12'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LISTA-100')
        self.assertContains(response, 'LISTA-VAC')
        self.assertContains(response, 'LISTA-LIC')
        self.assertContains(response, 'Vacaciones')
        self.assertContains(response, 'Licencia')
        self.assertContains(response, 'Ausente')
        self.assertEqual(response.context['total'], 3)
        tipo_vacaciones_mostrado = next(
            fila['valores'][2]
            for fila in response.context['filas']
            if 'LISTA-VAC' in str(fila['valores'][0])
        )
        tipo_licencia_mostrado = next(
            fila['valores'][2]
            for fila in response.context['filas']
            if 'LISTA-LIC' in str(fila['valores'][0])
        )
        self.assertEqual(tipo_vacaciones_mostrado, 'Vacaciones')
        self.assertEqual(tipo_licencia_mostrado, 'Licencia')

    def test_detalle_mensual_muestra_asistencias_licencias_y_avisos(self):
        hoy = date.today()
        mes = f'{hoy.year:04d}-{hoy.month:02d}'
        RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=hoy,
            tipo=RegistroAsistencia.Tipo.TARDANZA,
            hora_ingreso=None,
            minutos_tardanza=12,
            minutos_extra=30,
            observaciones='Marcación fuera de horario.',
        )
        tipo_licencia = TipoLicencia.objects.create(
            codigo='MENSUAL-LIC',
            nombre='Licencia médica',
        )
        SolicitudLicencia.objects.create(
            empleado=self.empleado,
            tipo_licencia=tipo_licencia,
            fecha_inicio=hoy,
            fecha_fin=hoy,
            dias_solicitados='2.5',
            estado=SolicitudLicencia.Estado.PENDIENTE,
            motivo='Control médico',
        )
        incidencia = Incidencia.objects.create(
            empleado=self.empleado,
            categoria=Incidencia.Categoria.ASISTENCIA,
            titulo='Revisar fichaje',
            descripcion='Se debe verificar el registro de entrada.',
        )

        response = self.client.get(
            f'/asistencia/empleados/{self.empleado.pk}/',
            {'mes': mes},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resumen mensual de asistencia')
        self.assertContains(response, '12 min')
        self.assertContains(response, '30 min')
        self.assertContains(response, 'Licencia médica')
        self.assertContains(response, '2,5 días')
        self.assertContains(response, '2,5')
        self.assertContains(response, 'Control médico')
        self.assertContains(response, incidencia.numero)
        self.assertContains(response, 'Revisar fichaje')
        self.assertEqual(response.context['resumen']['tardanzas'], 1)
        self.assertEqual(response.context['resumen']['horas_extra_minutos'], 30)
        self.assertEqual(response.context['resumen']['licencias'], 2.5)
