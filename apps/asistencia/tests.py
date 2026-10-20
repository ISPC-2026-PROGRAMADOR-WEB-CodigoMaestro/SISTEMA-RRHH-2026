import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.db import connection
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import PerfilUsuario
from apps.empleados.models import Empleado
from apps.licencias.models import SolicitudLicencia, TipoLicencia

from .models import (
    AsignacionJornada,
    Feriado,
    Jornada,
    Marcacion,
    RegistroAsistencia,
    Turno,
)
from .services import (
    cerrar_dia,
    consolidar_dia,
    importar_marcaciones,
    registrar_marcacion,
)


class CalculoAsistenciaTests(TestCase):
    def setUp(self):
        self.empleado = Empleado.objects.create(
            legajo='A-100',
            numero_documento='200',
            apellido='Gómez',
            nombre='Luis',
            fecha_ingreso=date(2024, 1, 1),
        )
        self.user = get_user_model().objects.create_user(username='cargador', password='test-password')
        self.turno = Turno.objects.create(
            nombre='Diurno',
            hora_inicio=time(9, 0),
            hora_fin=time(17, 0),
            minutos_tolerancia=10,
        )
        Jornada.objects.create(
            empleado=self.empleado,
            turno=self.turno,
            dia_semana=0,
            vigencia_desde=date(2026, 1, 1),
        )

    def test_calcula_tardanza_y_horas_extra_desde_el_turno(self):
        registro = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 12),
            hora_ingreso=time(9, 20),
            hora_egreso=time(17, 45),
            cargado_por=self.user,
        )

        self.assertEqual(registro.minutos_tardanza, 10)
        self.assertEqual(registro.minutos_extra, 45)

    def test_no_cuenta_una_salida_temprana_como_horas_extra(self):
        registro = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 12),
            hora_ingreso=time(9, 0),
            hora_egreso=time(8, 0),
        )

        self.assertEqual(registro.minutos_extra, 0)


class MarcacionesFixtureMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='fichaje-user', password='test-password',
        )
        self.empleado = self.crear_empleado('M-100', '100', self.user)
        self.jornada = Jornada.objects.create(
            nombre='Diurna',
            hora_entrada=time(9),
            hora_salida=time(18),
            tolerancia_minutos=10,
            dias_laborables='0,1,2,3,4',
        )
        AsignacionJornada.objects.create(
            empleado=self.empleado,
            jornada=self.jornada,
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

    def momento(self, dia, hora):
        return timezone.make_aware(
            datetime.combine(dia, hora),
            timezone.get_current_timezone(),
        )

    def marcar_dia(self, dia, entrada, salida=None):
        marcas = [
            Marcacion(
                empleado=self.empleado,
                fecha_hora=self.momento(dia, entrada),
                tipo=Marcacion.Tipo.ENTRADA,
                origen=Marcacion.Origen.MANUAL,
            ),
        ]
        if salida:
            marcas.append(Marcacion(
                empleado=self.empleado,
                fecha_hora=self.momento(dia, salida),
                tipo=Marcacion.Tipo.SALIDA,
                origen=Marcacion.Origen.MANUAL,
            ))
        Marcacion.objects.bulk_create(marcas)
        return consolidar_dia(self.empleado, dia)


class MarcacionesServiceTests(MarcacionesFixtureMixin, TestCase):
    def test_marcacion_alterna_entrada_y_salida(self):
        instante = self.momento(date(2026, 10, 12), time(9))
        entrada = registrar_marcacion(
            self.empleado, Marcacion.Origen.WEB, momento=instante,
        )
        salida = registrar_marcacion(
            self.empleado,
            Marcacion.Origen.WEB,
            momento=instante + timedelta(hours=9),
        )

        self.assertEqual(entrada.tipo, Marcacion.Tipo.ENTRADA)
        self.assertEqual(salida.tipo, Marcacion.Tipo.SALIDA)
        registro = RegistroAsistencia.objects.get(empleado=self.empleado, fecha=instante.date())
        self.assertEqual(registro.hora_ingreso, time(9))
        self.assertEqual(registro.hora_egreso, time(18))

    def test_bloquea_doble_clic_durante_sesenta_segundos(self):
        instante = self.momento(date(2026, 10, 12), time(9))
        registrar_marcacion(self.empleado, Marcacion.Origen.WEB, momento=instante)

        with self.assertRaises(ValidationError):
            registrar_marcacion(
                self.empleado,
                Marcacion.Origen.WEB,
                momento=instante + timedelta(seconds=59),
            )
        self.assertEqual(Marcacion.objects.count(), 1)

    def test_marcacion_explicita_rechaza_salida_antes_de_llegada(self):
        instante = self.momento(date(2026, 10, 12), time(9))

        with self.assertRaises(ValidationError):
            registrar_marcacion(
                self.empleado,
                Marcacion.Origen.WEB,
                momento=instante,
                tipo=Marcacion.Tipo.SALIDA,
            )
        llegada = registrar_marcacion(
            self.empleado,
            Marcacion.Origen.WEB,
            momento=instante,
            tipo=Marcacion.Tipo.ENTRADA,
        )
        salida = registrar_marcacion(
            self.empleado,
            Marcacion.Origen.WEB,
            momento=instante + timedelta(hours=9),
            tipo=Marcacion.Tipo.SALIDA,
        )

        self.assertEqual(llegada.tipo, Marcacion.Tipo.ENTRADA)
        self.assertEqual(salida.tipo, Marcacion.Tipo.SALIDA)

    def test_calcula_tardanza_en_limite_y_fuera_de_tolerancia(self):
        dentro = self.marcar_dia(date(2026, 10, 12), time(9, 10), time(18))
        self.assertEqual(dentro.minutos_tardanza, 0)

        tarde = self.marcar_dia(date(2026, 10, 13), time(9, 12), time(18))
        self.assertEqual(tarde.minutos_tardanza, 2)
        self.assertEqual(tarde.tipo, RegistroAsistencia.Tipo.TARDANZA)

    def test_calcula_horas_extra_y_retiro_temprano(self):
        extra = self.marcar_dia(date(2026, 10, 12), time(9), time(18, 45))
        self.assertEqual(extra.minutos_extra, 45)
        temprano = self.marcar_dia(date(2026, 10, 13), time(9), time(17, 30))
        self.assertEqual(temprano.tipo, RegistroAsistencia.Tipo.RETIRO_ANTICIPADO)

    def test_consolidacion_respeta_justificacion_y_tipo_manual(self):
        fecha = date(2026, 10, 12)
        registro = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=fecha,
            tipo=RegistroAsistencia.Tipo.HOME_OFFICE,
            justificado=True,
            justificacion='Trabajo remoto autorizado.',
            observaciones='Observación manual.',
            minutos_tardanza=7,
        )
        Marcacion.objects.create(
            empleado=self.empleado,
            fecha_hora=self.momento(fecha, time(9)),
            tipo=Marcacion.Tipo.ENTRADA,
        )
        consolidado = consolidar_dia(self.empleado, fecha)
        consolidado.refresh_from_db()

        self.assertEqual(consolidado.tipo, RegistroAsistencia.Tipo.HOME_OFFICE)
        self.assertTrue(consolidado.justificado)
        self.assertEqual(consolidado.justificacion, 'Trabajo remoto autorizado.')
        self.assertEqual(consolidado.observaciones, 'Observación manual.')
        self.assertEqual(consolidado.minutos_tardanza, 7)
        self.assertEqual(consolidado.hora_ingreso, time(9))

    def test_consolidacion_sola_entrada_informa_falta_de_salida(self):
        registro = self.marcar_dia(date(2026, 10, 12), time(9))
        self.assertIsNone(registro.hora_egreso)
        self.assertIn('Sin marcación de salida', registro.observaciones)

    def test_cerrar_dia_genera_vacaciones_licencias_y_ausencias(self):
        lunes = date(2026, 10, 12)
        viernes = date(2026, 10, 9)
        sabado = date(2026, 10, 10)
        domingo = date(2026, 10, 11)
        empleado_con_vacaciones = self.crear_empleado('M-101', '101')
        empleado_con_licencia = self.crear_empleado('M-102', '102')
        AsignacionJornada.objects.create(
            empleado=empleado_con_vacaciones,
            jornada=self.jornada,
        )
        AsignacionJornada.objects.create(
            empleado=empleado_con_licencia,
            jornada=self.jornada,
        )
        Feriado.objects.create(fecha=lunes, nombre='Feriado de prueba')
        tipo_vacaciones = TipoLicencia.objects.create(
            codigo='TEST-VAC',
            nombre='Vacaciones',
            descuenta_vacaciones=True,
        )
        tipo_licencia = TipoLicencia.objects.create(
            codigo='TEST-LIC',
            nombre='Licencia',
        )
        SolicitudLicencia.objects.create(
            empleado=empleado_con_vacaciones,
            tipo_licencia=tipo_vacaciones,
            fecha_inicio=viernes,
            fecha_fin=lunes,
            dias_solicitados=Decimal('1'),
            estado=SolicitudLicencia.Estado.APROBADA,
        )
        SolicitudLicencia.objects.create(
            empleado=empleado_con_licencia,
            tipo_licencia=tipo_licencia,
            fecha_inicio=date(2026, 10, 13),
            fecha_fin=date(2026, 10, 13),
            dias_solicitados=Decimal('1'),
            estado=SolicitudLicencia.Estado.APROBADA,
        )

        resumen_viernes = cerrar_dia(viernes)
        resumen_viernes_repetido = cerrar_dia(viernes)
        resumen_sabado = cerrar_dia(sabado)
        resumen_domingo = cerrar_dia(domingo)
        resumen_lunes = cerrar_dia(lunes)
        resumen_martes = cerrar_dia(date(2026, 10, 13))

        self.assertEqual(resumen_viernes['licencias_creadas'], 1)
        self.assertEqual(resumen_viernes_repetido['licencias_creadas'], 0)
        self.assertEqual(resumen_sabado['licencias_creadas'], 0)
        self.assertEqual(resumen_domingo['licencias_creadas'], 0)
        self.assertEqual(resumen_lunes['licencias_creadas'], 0)
        self.assertEqual(resumen_martes['licencias_creadas'], 1)
        self.assertEqual(
            RegistroAsistencia.objects.get(
                empleado=empleado_con_vacaciones,
                fecha=viernes,
            ).tipo,
            RegistroAsistencia.Tipo.VACACIONES,
        )
        self.assertFalse(RegistroAsistencia.objects.filter(
            empleado=empleado_con_vacaciones,
            fecha__in=[sabado, domingo, lunes],
        ).exists())
        self.assertEqual(
            RegistroAsistencia.objects.get(
                empleado=empleado_con_licencia,
                fecha=date(2026, 10, 13),
            ).tipo,
            RegistroAsistencia.Tipo.LICENCIA,
        )
        self.assertEqual(
            RegistroAsistencia.objects.get(empleado=self.empleado, fecha=viernes).tipo,
            RegistroAsistencia.Tipo.AUSENTE,
        )
        self.assertFalse(RegistroAsistencia.objects.filter(fecha=lunes).exists())
        self.assertEqual(cerrar_dia(viernes)['ausentes_creados'], 0)

    def test_cerrar_dia_conserva_marcacion_y_anota_fichaje_durante_licencia(self):
        fecha = date(2026, 10, 12)
        tipo = TipoLicencia.objects.create(
            codigo='TEST-LIC',
            nombre='Licencia',
        )
        SolicitudLicencia.objects.create(
            empleado=self.empleado,
            tipo_licencia=tipo,
            fecha_inicio=fecha,
            fecha_fin=fecha,
            dias_solicitados=Decimal('1'),
            estado=SolicitudLicencia.Estado.APROBADA,
        )
        Marcacion.objects.create(
            empleado=self.empleado,
            fecha_hora=self.momento(fecha, time(9)),
            tipo=Marcacion.Tipo.ENTRADA,
            origen=Marcacion.Origen.WEB,
        )

        resumen = cerrar_dia(fecha)
        registro = RegistroAsistencia.objects.get(empleado=self.empleado, fecha=fecha)

        self.assertEqual(resumen['consolidados'], 1)
        self.assertEqual(Marcacion.objects.filter(empleado=self.empleado).count(), 1)
        self.assertEqual(registro.tipo, RegistroAsistencia.Tipo.PRESENTE)
        self.assertIn(
            'Marcación realizada durante una solicitud de licencia o vacaciones.',
            registro.observaciones,
        )

    def test_cerrar_dia_actualiza_ausente_existente_a_vacaciones_aprobadas(self):
        fecha = date(2026, 10, 12)
        registro = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=fecha,
            tipo=RegistroAsistencia.Tipo.AUSENTE,
            observaciones='Ausencia generada por cierre.',
        )
        tipo_vacaciones = TipoLicencia.objects.create(
            codigo='TEST-VAC',
            nombre='Vacaciones',
            descuenta_vacaciones=True,
        )
        SolicitudLicencia.objects.create(
            empleado=self.empleado,
            tipo_licencia=tipo_vacaciones,
            fecha_inicio=fecha,
            fecha_fin=fecha,
            dias_solicitados=Decimal('1'),
            estado=SolicitudLicencia.Estado.PENDIENTE,
        )

        resumen = cerrar_dia(fecha)
        registro.refresh_from_db()

        self.assertEqual(resumen['licencias_creadas'], 1)
        self.assertEqual(registro.tipo, RegistroAsistencia.Tipo.VACACIONES)
        self.assertEqual(registro.observaciones, 'Ausencia generada por cierre.')

    def test_cerrar_dia_crea_ausente_para_empleado_activo_sin_jornada(self):
        empleado_sin_jornada = self.crear_empleado('M-103', '103')
        fecha = date(2026, 10, 12)

        resumen = cerrar_dia(fecha)

        self.assertEqual(resumen['ausentes_creados'], 2)
        self.assertEqual(
            RegistroAsistencia.objects.get(
                empleado=empleado_sin_jornada,
                fecha=fecha,
            ).tipo,
            RegistroAsistencia.Tipo.AUSENTE,
        )

    def test_cerrar_dia_limita_consultas_para_ciento_cincuenta_empleados(self):
        Jornada.objects.filter(pk=self.jornada.pk).update(dias_laborables='0,1,2,3,4')
        empleados = [
            Empleado(
                legajo=f'B-{i:03}',
                numero_documento=f'B-{i:03}',
                apellido='Lote',
                nombre=f'Empleado {i}',
                fecha_ingreso=date(2020, 1, 1),
            )
            for i in range(150)
        ]
        Empleado.objects.bulk_create(empleados)
        empleados = list(Empleado.objects.filter(legajo__startswith='B-'))
        AsignacionJornada.objects.bulk_create([
            AsignacionJornada(empleado=empleado, jornada=self.jornada)
            for empleado in empleados
        ])

        with CaptureQueriesContext(connection) as consultas:
            resumen = cerrar_dia(date(2026, 10, 12))

        self.assertLess(len(consultas), 15)
        self.assertEqual(resumen['ausentes_creados'], 151)


class ImportarMarcacionesTests(MarcacionesFixtureMixin, TestCase):
    def archivo(self, contenido, nombre='marcas.csv'):
        return SimpleUploadedFile(
            nombre,
            contenido.encode('utf-8'),
            content_type='text/csv',
        )

    def test_importa_csv_con_comas_y_tipos(self):
        archivo = self.archivo(
            'legajo,fecha,hora,tipo\n'
            'M-100,12/10/2026,09:00,ENTRADA\n'
            'M-100,12/10/2026,18:00,SALIDA\n'
        )

        resumen = importar_marcaciones(archivo, self.user)

        self.assertEqual(resumen['creadas'], 2)
        self.assertEqual(resumen['errores'], [])
        registro = RegistroAsistencia.objects.get(empleado=self.empleado, fecha=date(2026, 10, 12))
        self.assertEqual(registro.hora_egreso, time(18))

    def test_importa_csv_punto_y_coma_sin_tipo_e_ignora_intermedias(self):
        archivo = self.archivo(
            'legajo;fecha;hora\n'
            'M-100;2026-10-12;09:00\n'
            'M-100;2026-10-12;13:00\n'
            'M-100;2026-10-12;18:00\n'
        )

        resumen = importar_marcaciones(archivo, self.user)

        self.assertEqual(resumen['creadas'], 2)
        self.assertEqual(resumen['ignoradas'], 1)
        self.assertEqual(
            set(Marcacion.objects.values_list('tipo', flat=True)),
            {Marcacion.Tipo.ENTRADA, Marcacion.Tipo.SALIDA},
        )

    def test_importa_archivo_xlsx(self):
        from openpyxl import Workbook

        libro = Workbook()
        hoja = libro.active
        hoja.append(['legajo', 'fecha', 'hora', 'tipo'])
        hoja.append(['M-100', '12/10/2026', '09:00', 'E'])
        archivo_bytes = io.BytesIO()
        libro.save(archivo_bytes)
        archivo = SimpleUploadedFile(
            'marcas.xlsx',
            archivo_bytes.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        resumen = importar_marcaciones(archivo, self.user)

        self.assertEqual(resumen['creadas'], 1)
        self.assertEqual(Marcacion.objects.get().tipo, Marcacion.Tipo.ENTRADA)

    def test_reimportacion_no_duplica_marcaciones(self):
        contenido = (
            'legajo,fecha_hora,tipo\n'
            'M-100,2026-10-12 09:00,ENTRADA\n'
        )

        primera = importar_marcaciones(self.archivo(contenido), self.user)
        segunda = importar_marcaciones(self.archivo(contenido), self.user)

        self.assertEqual(primera['creadas'], 1)
        self.assertEqual(segunda['creadas'], 0)
        self.assertEqual(segunda['duplicadas'], 1)
        self.assertEqual(Marcacion.objects.count(), 1)

    def test_importacion_reporta_filas_invalidas_y_sigue(self):
        archivo = self.archivo(
            'legajo,fecha,hora,tipo\n'
            'NO-EXISTE,12/10/2026,09:00,ENTRADA\n'
            'M-100,fecha-mala,09:00,ENTRADA\n'
            'M-100,12/10/2026,09:00,ENTRADA\n'
        )

        resumen = importar_marcaciones(archivo, self.user)

        self.assertEqual(resumen['creadas'], 1)
        self.assertEqual([error['fila'] for error in resumen['errores']], [2, 3])
        self.assertEqual(Marcacion.objects.count(), 1)

    def test_rechaza_archivos_mayores_a_cinco_megabytes(self):
        archivo = SimpleUploadedFile(
            'grande.csv',
            b'x' * (5 * 1024 * 1024 + 1),
        )
        with self.assertRaises(ValidationError):
            importar_marcaciones(archivo, self.user)


class AsistenciaAPITests(MarcacionesFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        PerfilUsuario.objects.create(
            usuario=self.user,
            rol=PerfilUsuario.RolPredeterminado.SOLO_LECTURA,
        )
        self.client.force_authenticate(self.user)

    def test_rol_lectura_puede_fichar_pero_no_importar_ni_cerrar(self):
        respuesta = self.client.post('/api/asistencia/marcaciones/marcar/', {}, format='json')
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data['origen'], Marcacion.Origen.WEB)

        importacion = self.client.post('/api/asistencia/marcaciones/importar/', {}, format='multipart')
        cierre = self.client.post(
            '/api/asistencia/registros/cerrar-dia/',
            {'fecha': '2026-10-12'},
            format='json',
        )
        self.assertEqual(importacion.status_code, 403)
        self.assertEqual(cierre.status_code, 403)

    def test_usuario_sin_empleado_recibe_error_claro_al_fichar(self):
        usuario = get_user_model().objects.create_user(
            username='sin-legajo', password='test-password',
        )
        self.client.force_authenticate(usuario)

        respuesta = self.client.post('/api/asistencia/marcaciones/marcar/', {}, format='json')

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('vinculado a un legajo', respuesta.data['detail'])

    def test_marcacion_manual_crea_o_actualiza_resumen_diario(self):
        administrador = get_user_model().objects.create_superuser(
            username='admin-marcacion',
            password='test-password',
            email='admin-marcacion@example.com',
        )
        self.client.force_authenticate(administrador)
        respuesta = self.client.post(
            '/api/asistencia/marcaciones/',
            {
                'empleado': self.empleado.pk,
                'fecha_hora': self.momento(
                    date(2026, 10, 12), time(9),
                ).isoformat(),
                'tipo': Marcacion.Tipo.ENTRADA,
            },
            format='json',
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data['origen'], Marcacion.Origen.MANUAL)
        self.assertTrue(RegistroAsistencia.objects.filter(
            empleado=self.empleado, fecha=date(2026, 10, 12),
        ).exists())

    def test_mi_estado_muestra_proxima_salida_despues_de_fichar(self):
        respuesta = self.client.post('/api/asistencia/marcaciones/marcar/', {}, format='json')
        self.assertEqual(respuesta.status_code, 201)

        estado = self.client.get('/api/asistencia/marcaciones/mi-estado/')

        self.assertEqual(estado.status_code, 200)
        self.assertTrue(estado.data['falta_salida'])
        self.assertEqual(estado.data['proxima_accion'], Marcacion.Tipo.SALIDA)


class AsistenciaWebTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='web-fichaje', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='WEB-A',
            numero_documento='WEB-A',
            apellido='Web',
            nombre='Persona',
            fecha_ingreso=date(2020, 1, 1),
            usuario=self.user,
        )
        self.client.force_login(self.user)

    def test_pantalla_fichar_y_post_funcionan(self):
        self.client.logout()
        respuesta = self.client.get('/asistencia/fichar/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Número de legajo')
        self.assertContains(respuesta, 'Llegada')
        self.assertContains(respuesta, 'Salida')

        respuesta = self.client.post('/asistencia/fichar/', {
            'legajo': self.empleado.legajo,
            'accion': 'llegada',
        })

        self.assertRedirects(respuesta, '/asistencia/fichar/')
        self.assertEqual(Marcacion.objects.filter(empleado=self.empleado).count(), 1)
        self.assertIsNone(Marcacion.objects.get(empleado=self.empleado).cargado_por_id)
        registro = RegistroAsistencia.objects.get(empleado=self.empleado)
        self.assertEqual(registro.hora_ingreso, timezone.localtime(
            Marcacion.objects.get(empleado=self.empleado).fecha_hora
        ).time().replace(tzinfo=None))

    def test_fichaje_publico_acepta_legajo_de_empleado_sin_cuenta_vinculada(self):
        empleado = Empleado.objects.create(
            legajo='SIN-CUENTA',
            numero_documento='SIN-CUENTA',
            apellido='Sin',
            nombre='Cuenta',
            fecha_ingreso=date(2020, 1, 1),
        )
        self.client.logout()

        respuesta = self.client.post('/asistencia/fichar/', {
            'legajo': empleado.legajo,
            'accion': 'llegada',
        })

        self.assertRedirects(respuesta, '/asistencia/fichar/')
        self.assertTrue(Marcacion.objects.filter(empleado=empleado).exists())

    def test_fichaje_publico_rechaza_legajo_inexistente(self):
        self.client.logout()

        respuesta = self.client.post('/asistencia/fichar/', {
            'legajo': 'NO-EXISTE',
            'accion': 'llegada',
        })

        self.assertRedirects(respuesta, '/asistencia/fichar/')
        self.assertFalse(Marcacion.objects.exists())

    def test_control_asistencia_abre_fichaje_en_otra_pestana(self):
        administrador = get_user_model().objects.create_superuser(
            username='web-admin-asistencia',
            password='test-password',
            email='web-admin-asistencia@example.com',
        )
        self.client.force_login(administrador)

        respuesta = self.client.get('/m/asistencia/')

        self.assertContains(respuesta, 'Abrir ventana de fichaje')
        self.assertContains(respuesta, 'target="_blank"')
        self.assertContains(respuesta, 'Día terminado')

    def test_boton_dia_terminado_cierra_el_dia_actual(self):
        administrador = get_user_model().objects.create_superuser(
            username='web-admin-cierre',
            password='test-password',
            email='web-admin-cierre@example.com',
        )
        self.client.force_login(administrador)
        hoy = date(2026, 10, 12)
        jornada = Jornada.objects.create(
            nombre='Jornada de cierre',
            hora_entrada=time(9),
            hora_salida=time(18),
            dias_laborables='0,1,2,3,4',
        )
        AsignacionJornada.objects.create(
            empleado=self.empleado,
            jornada=jornada,
        )

        with patch('apps.asistencia.web_views.timezone.localdate', return_value=hoy):
            respuesta = self.client.post('/asistencia/cerrar-hoy/')

        self.assertRedirects(respuesta, '/m/asistencia/')
        registro = RegistroAsistencia.objects.get(empleado=self.empleado, fecha=hoy)
        self.assertEqual(registro.tipo, RegistroAsistencia.Tipo.AUSENTE)

    def test_boton_dia_terminado_requiere_rol_operativo(self):
        respuesta = self.client.post('/asistencia/cerrar-hoy/')
        self.assertEqual(respuesta.status_code, 403)

    def test_boton_dia_terminado_no_acepta_get(self):
        administrador = get_user_model().objects.create_superuser(
            username='web-admin-cierre-get',
            password='test-password',
            email='web-admin-cierre-get@example.com',
        )
        self.client.force_login(administrador)

        respuesta = self.client.get('/asistencia/cerrar-hoy/')

        self.assertEqual(respuesta.status_code, 405)

    def test_importar_web_requiere_rol_operativo(self):
        respuesta = self.client.get('/asistencia/importar/')
        self.assertEqual(respuesta.status_code, 403)


class AsistenciaCommandTests(TestCase):
    def test_cargar_asistencia_demo_es_idempotente(self):
        user_model = get_user_model()
        user_model.objects.get_or_create(
            username='rrhh',
            defaults={'password': 'test-password'},
        )
        Empleado.objects.create(
            legajo='DEMO-1',
            numero_documento='DEMO-1',
            apellido='Demo',
            nombre='Empleado',
            fecha_ingreso=date(2020, 1, 1),
        )

        call_command('cargar_asistencia_demo', stdout=io.StringIO())
        cantidad_marcaciones = Marcacion.objects.count()
        cantidad_registros = RegistroAsistencia.objects.count()
        call_command('cargar_asistencia_demo', stdout=io.StringIO())

        self.assertEqual(Jornada.objects.filter(es_predeterminada=True).count(), 1)
        self.assertEqual(AsignacionJornada.objects.count(), 1)
        self.assertEqual(Marcacion.objects.count(), cantidad_marcaciones)
        self.assertEqual(RegistroAsistencia.objects.count(), cantidad_registros)
        self.assertEqual(Empleado.objects.get(legajo='DEMO-1').usuario.username, 'rrhh')

    def test_comando_cerrar_asistencia_acepta_fecha(self):
        salida = io.StringIO()

        call_command('cerrar_asistencia', '--fecha', '2026-10-12', stdout=salida)

        self.assertIn('2026-10-12:', salida.getvalue())
