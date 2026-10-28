from datetime import date, time
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook

from apps.accounts.models import PerfilUsuario
from apps.asistencia.models import AsignacionJornada, Jornada, RegistroAsistencia, Turno
from apps.horarios_laborales.models import HorarioDiario, HorarioPredeterminado
from apps.asistencia.services import obtener_horario_esperado
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
        turno = Turno.objects.create(
            nombre='Turno resumen mensual',
            hora_inicio=time(9),
            hora_fin=time(18),
            minutos_tolerancia=10,
        )
        Jornada.objects.create(
            empleado=self.empleado,
            turno=turno,
            dia_semana=hoy.weekday(),
            vigencia_desde=hoy,
        )
        RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=hoy,
            tipo=RegistroAsistencia.Tipo.TARDANZA,
            hora_ingreso=time(9, 22),
            hora_egreso=time(18, 30),
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

    def test_detalle_mensual_muestra_horario_y_metricas_calculadas_con_ese_horario(self):
        hoy = date.today()
        HorarioDiario.objects.create(
            empleado=self.empleado,
            fecha=hoy,
            hora_entrada=time(10),
            hora_salida=time(19),
        )
        registro = RegistroAsistencia.objects.create(
            empleado=self.empleado,
            fecha=hoy,
            hora_ingreso=time(10, 22),
            hora_egreso=time(19, 30),
        )

        response = self.client.get(
            f'/asistencia/empleados/{self.empleado.pk}/',
            {'mes': f'{hoy.year:04d}-{hoy.month:02d}'},
        )

        self.assertEqual(response.status_code, 200)
        registro = response.context['registros'][0]
        self.assertEqual(registro.horario_esperado.inicio.time(), time(10))
        self.assertEqual(registro.horario_esperado.fin.time(), time(19))
        self.assertEqual(registro.minutos_tardanza, 12)
        self.assertEqual(registro.minutos_extra, 30)
        self.assertContains(response, '10:00–19:00')


class HorariosLaboralesDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='horarios-dashboard-empleado',
            password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='HOR-WEB-100',
            numero_documento='HOR-WEB-100',
            apellido='Horario',
            nombre='Empleado',
            fecha_ingreso=date(2020, 1, 1),
            usuario=self.user,
        )
        self.otro_empleado = Empleado.objects.create(
            legajo='HOR-WEB-200',
            numero_documento='HOR-WEB-200',
            apellido='Otro',
            nombre='Empleado',
            fecha_ingreso=date(2020, 1, 1),
        )
        self.rrhh = get_user_model().objects.create_user(
            username='horarios-dashboard-rrhh',
            password='test-password',
        )
        PerfilUsuario.objects.create(
            usuario=self.rrhh,
            rol=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
        )
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

    def test_menu_muestra_apartado_horarios_laborales(self):
        self.client.force_login(self.user)

        response = self.client.get('/horarios-laborales/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Horarios laborales')
        self.assertContains(response, 'Jornada laboral')
        self.assertContains(response, '09:00')
        self.assertNotContains(response, '10:00')
        self.assertContains(response, 'href="/horarios-laborales/"')

    def test_formulario_muestra_opciones_de_aplicacion_legibles(self):
        self.client.force_login(self.rrhh)

        response = self.client.get('/horarios-laborales/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<fieldset class="mb-3">')
        self.assertContains(response, 'Solo esta fecha')
        self.assertContains(response, 'Cambiar el horario predeterminado desde esta fecha')
        self.assertContains(response, 'class="form-check-input" type="radio"')

    def test_filtro_por_rango_de_fechas(self):
        self.client.force_login(self.user)

        response = self.client.get(
            '/horarios-laborales/',
            {'fecha_desde': '2026-10-22', 'fecha_hasta': '2026-10-23'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay horarios para el período seleccionado.')
        self.assertNotContains(response, '09:00')

    def test_administrativo_puede_ver_horarios_de_todos_los_empleados(self):
        self.client.force_login(self.rrhh)

        response = self.client.get('/horarios-laborales/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Horario, Empleado')
        self.assertContains(response, 'Otro, Empleado')

    def test_administrativo_crea_horario_individual(self):
        self.client.force_login(self.rrhh)

        response = self.client.post('/horarios-laborales/', {
            'accion': 'crear_individual',
            'empleado': self.otro_empleado.pk,
            'fecha': '2026-10-22',
            'hora_entrada': '08:00',
            'hora_salida': '17:00',
            'es_franco': '',
            'observaciones': 'Turno cargado por formulario',
            'alcance': 'solo_fecha',
        })

        self.assertRedirects(response, '/horarios-laborales/')
        horario = HorarioDiario.objects.get(
            empleado=self.otro_empleado,
            fecha=date(2026, 10, 22),
        )
        self.assertEqual(horario.hora_entrada, time(8))
        self.assertEqual(horario.creado_por, self.rrhh)

    def test_empleado_no_puede_cargar_horarios(self):
        self.client.force_login(self.user)

        response = self.client.post('/horarios-laborales/', {
            'accion': 'crear_individual',
        })

        self.assertEqual(response.status_code, 403)

    def test_carga_masiva_permite_confirmar_reemplazo_explicito(self):
        self.client.force_login(self.rrhh)
        contenido = (
            'legajo,fecha,hora_entrada,hora_salida,es_franco,observaciones\n'
            'HOR-WEB-100,2026-10-21,08:00,17:00,No,Horario reemplazado\n'
            'HOR-WEB-200,2026-10-22,09:00,18:00,No,Nuevo horario\n'
        ).encode('utf-8')
        archivo = SimpleUploadedFile(
            'horarios.csv',
            contenido,
            content_type='text/csv',
        )

        response = self.client.post(
            '/horarios-laborales/',
            {'accion': 'previsualizar_archivo', 'archivo_horarios': archivo},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reemplazar existente')
        token = response.context['token_previsualizacion']
        response = self.client.post('/horarios-laborales/', {
            'accion': 'confirmar_archivo',
            'token': token,
            'reemplazar_0': 'on',
        })

        self.assertRedirects(response, '/horarios-laborales/')
        self.horario_propio.refresh_from_db()
        self.assertEqual(self.horario_propio.hora_entrada, time(8))
        self.assertEqual(
            HorarioDiario.objects.get(
                empleado=self.otro_empleado,
                fecha=date(2026, 10, 22),
            ).hora_entrada,
            time(9),
        )

    def test_carga_masiva_omite_duplicado_no_seleccionado(self):
        self.client.force_login(self.rrhh)
        archivo = SimpleUploadedFile(
            'horarios.csv',
            (
                'legajo,fecha,hora_entrada,hora_salida,es_franco,observaciones\n'
                'HOR-WEB-100,2026-10-21,08:00,17:00,No,No reemplazar\n'
            ).encode('utf-8'),
            content_type='text/csv',
        )

        response = self.client.post(
            '/horarios-laborales/',
            {'accion': 'previsualizar_archivo', 'archivo_horarios': archivo},
            follow=True,
        )
        response = self.client.post('/horarios-laborales/', {
            'accion': 'confirmar_archivo',
            'token': response.context['token_previsualizacion'],
        })

        self.assertRedirects(response, '/horarios-laborales/')
        self.horario_propio.refresh_from_db()
        self.assertEqual(self.horario_propio.hora_entrada, time(9))

    def test_primera_carga_se_convierte_en_horario_predeterminado(self):
        self.client.force_login(self.rrhh)
        archivo = SimpleUploadedFile(
            'horarios.csv',
            (
                'legajo,fecha,hora_entrada,hora_salida,es_franco,observaciones\n'
                'HOR-WEB-200,2026-10-26,12:00,18:00,No,Horario base\n'
            ).encode('utf-8'),
            content_type='text/csv',
        )

        response = self.client.post(
            '/horarios-laborales/',
            {'accion': 'previsualizar_archivo', 'archivo_horarios': archivo},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        fila = response.context['filas_previsualizadas'][0]
        self.assertTrue(fila['predeterminado_inicial'])
        self.client.post('/horarios-laborales/', {
            'accion': 'confirmar_archivo',
            'token': response.context['token_previsualizacion'],
        })
        horario_base = HorarioPredeterminado.objects.get(
            empleado=self.otro_empleado,
        )
        self.assertEqual(horario_base.vigente_desde, date(2026, 10, 26))
        self.assertEqual(horario_base.hora_entrada, time(12))

    def test_nuevo_predeterminado_reemplaza_versiones_futuras_y_conserva_historial(self):
        anterior = HorarioPredeterminado.objects.create(
            empleado=self.empleado,
            vigente_desde=date(2026, 10, 20),
            hora_entrada=time(9),
            hora_salida=time(17),
        )
        futuro = HorarioPredeterminado.objects.create(
            empleado=self.empleado,
            vigente_desde=date(2026, 11, 1),
            hora_entrada=time(10),
            hora_salida=time(18),
        )
        self.client.force_login(self.rrhh)

        response = self.client.post('/horarios-laborales/', {
            'accion': 'crear_individual',
            'empleado': self.empleado.pk,
            'fecha': '2026-10-28',
            'hora_entrada': '12:00',
            'hora_salida': '18:00',
            'es_franco': '',
            'observaciones': 'Nuevo horario base',
            'alcance': 'predeterminado',
        })

        self.assertRedirects(response, '/horarios-laborales/')
        self.assertTrue(
            HorarioPredeterminado.objects.filter(pk=anterior.pk).exists()
        )
        self.assertFalse(
            HorarioPredeterminado.objects.filter(pk=futuro.pk).exists()
        )
        nuevo = HorarioPredeterminado.objects.get(
            empleado=self.empleado,
            vigente_desde=date(2026, 10, 28),
        )
        self.assertEqual(nuevo.hora_entrada, time(12))

    def test_horario_de_un_dia_retorna_al_predeterminado_despues(self):
        base = Jornada.objects.create(
            nombre='Jornada base semanal',
            hora_entrada=time(9),
            hora_salida=time(17),
            dias_laborables='0,1,2,3,4',
        )
        AsignacionJornada.objects.create(
            empleado=self.empleado,
            jornada=base,
        )
        HorarioPredeterminado.objects.create(
            empleado=self.empleado,
            vigente_desde=date(2026, 10, 26),
            hora_entrada=time(12),
            hora_salida=time(18),
        )
        HorarioDiario.objects.create(
            empleado=self.empleado,
            fecha=date(2026, 10, 27),
            hora_entrada=time(14),
            hora_salida=time(20),
        )

        horario_base = obtener_horario_esperado(
            self.empleado,
            date(2026, 10, 26),
        )
        horario_excepcion = obtener_horario_esperado(
            self.empleado,
            date(2026, 10, 27),
        )
        horario_dia_siguiente = obtener_horario_esperado(
            self.empleado,
            date(2026, 10, 28),
        )

        self.assertEqual(horario_base.inicio.time(), time(12))
        self.assertEqual(horario_excepcion.inicio.time(), time(14))
        self.assertEqual(horario_dia_siguiente.inicio.time(), time(12))

    def test_horario_predeterminado_respeta_dias_laborables_de_jornada(self):
        base = Jornada.objects.create(
            nombre='Jornada de lunes a viernes',
            hora_entrada=time(9),
            hora_salida=time(17),
            dias_laborables='0,1,2,3,4',
        )
        AsignacionJornada.objects.create(
            empleado=self.empleado,
            jornada=base,
        )
        HorarioPredeterminado.objects.create(
            empleado=self.empleado,
            vigente_desde=date(2026, 10, 26),
            hora_entrada=time(12),
            hora_salida=time(18),
        )

        horario_laborable = obtener_horario_esperado(
            self.empleado,
            date(2026, 10, 26),
        )
        horario_franco = obtener_horario_esperado(
            self.empleado,
            date(2026, 10, 31),
        )

        self.assertEqual(horario_laborable.inicio.time(), time(12))
        self.assertIsNone(horario_franco)

    def test_carga_xlsx_admite_turno_nocturno_y_franco(self):
        self.client.force_login(self.rrhh)
        libro = Workbook()
        hoja = libro.active
        hoja.append([
            'legajo',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'es_franco',
            'observaciones',
        ])
        hoja.append([
            'HOR-WEB-200',
            date(2026, 10, 23),
            time(22),
            time(6),
            False,
            'Turno nocturno',
        ])
        hoja.append([
            'HOR-WEB-200',
            date(2026, 10, 24),
            None,
            None,
            True,
            'Franco',
        ])
        contenido = BytesIO()
        libro.save(contenido)
        archivo = SimpleUploadedFile(
            'horarios.xlsx',
            contenido.getvalue(),
            content_type=(
                'application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.sheet'
            ),
        )

        response = self.client.post(
            '/horarios-laborales/',
            {'accion': 'previsualizar_archivo', 'archivo_horarios': archivo},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['filas_previsualizadas']), 2)
        self.client.post('/horarios-laborales/', {
            'accion': 'confirmar_archivo',
            'token': response.context['token_previsualizacion'],
        })

        nocturno = HorarioDiario.objects.get(
            empleado=self.otro_empleado,
            fecha=date(2026, 10, 23),
        )
        franco = HorarioDiario.objects.get(
            empleado=self.otro_empleado,
            fecha=date(2026, 10, 24),
        )
        self.assertEqual(nocturno.hora_entrada, time(22))
        self.assertEqual(nocturno.hora_salida, time(6))
        self.assertTrue(franco.es_franco)
        self.assertIsNone(franco.hora_entrada)

    def test_descarga_plantilla_requiere_rol_de_gestion(self):
        self.client.force_login(self.user)

        response = self.client.get('/horarios-laborales/plantilla/')

        self.assertEqual(response.status_code, 403)
