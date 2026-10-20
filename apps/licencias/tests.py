from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.asistencia.models import Feriado
from apps.empleados.models import Empleado

from .models import SaldoVacaciones, SolicitudLicencia, TipoLicencia
from .serializers import SolicitudLicenciaSerializer
from .services import (
    aprobar_solicitud,
    calcular_dias_habiles,
    cancelar_solicitud,
    dias_vacaciones_por_antiguedad,
    validar_solicitud,
)


class LicenciasServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='test-dev2-licencias', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='L-100',
            numero_documento='100',
            apellido='Pérez',
            nombre='Ana',
            fecha_ingreso=date(2020, 1, 1),
        )
        self.tipo = TipoLicencia.objects.create(
            codigo='TEST-VAC',
            nombre='Vacaciones',
            descuenta_vacaciones=True,
        )

    def crear_solicitud(self, inicio=date(2026, 12, 7), fin=date(2026, 12, 11)):
        return SolicitudLicencia.objects.create(
            empleado=self.empleado,
            tipo_licencia=self.tipo,
            fecha_inicio=inicio,
            fecha_fin=fin,
            dias_solicitados=calcular_dias_habiles(inicio, fin),
            solicitado_por=self.user,
        )

    def test_calcula_dias_habiles_excluyendo_fines_de_semana_y_feriados(self):
        Feriado.objects.create(fecha=date(2026, 12, 9), nombre='Feriado de prueba')

        self.assertEqual(
            calcular_dias_habiles(date(2026, 12, 7), date(2026, 12, 13)),
            Decimal('4'),
        )

    def test_validar_solicitud_rechaza_solapamiento(self):
        self.crear_solicitud()

        with self.assertRaises(ValidationError):
            validar_solicitud(
                self.empleado, self.tipo, date(2026, 12, 9), date(2026, 12, 14),
            )

    def test_api_calcula_dias_solicitados_y_no_acepta_valor_cliente(self):
        serializer = SolicitudLicenciaSerializer(data={
            'empleado': self.empleado.pk,
            'tipo_licencia': self.tipo.pk,
            'fecha_inicio': '2026-12-07',
            'fecha_fin': '2026-12-11',
            'dias_solicitados': '99',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        solicitud = serializer.save(solicitado_por=self.user)
        self.assertEqual(solicitud.dias_solicitados, Decimal('5'))

    def test_aprobar_vuelve_a_validar_solapamientos(self):
        primera = self.crear_solicitud()
        segunda = self.crear_solicitud(
            date(2026, 12, 9),
            date(2026, 12, 14),
        )

        with self.assertRaises(ValidationError):
            aprobar_solicitud(primera.pk, self.user)

        primera.refresh_from_db()
        segunda.refresh_from_db()
        self.assertEqual(primera.estado, SolicitudLicencia.Estado.PENDIENTE)
        self.assertEqual(segunda.estado, SolicitudLicencia.Estado.PENDIENTE)

    def test_aprobar_y_cancelar_actualiza_el_saldo_y_el_historial(self):
        Feriado.objects.create(fecha=date(2026, 12, 9), nombre='Feriado de prueba')
        solicitud = self.crear_solicitud()

        solicitud = aprobar_solicitud(solicitud.pk, self.user)

        saldo = SaldoVacaciones.objects.get(empleado=self.empleado, anio=2026)
        self.assertEqual(saldo.dias_correspondientes, Decimal('21'))
        self.assertEqual(saldo.dias_usados, Decimal('4'))
        self.assertEqual(saldo.dias_pendientes, Decimal('17'))
        self.assertEqual(self.empleado.historial.count(), 1)
        self.assertEqual(solicitud.dias_descontados, {'2026': '4'})

        Feriado.objects.all().delete()
        cancelar_solicitud(solicitud.pk, self.user)

        saldo.refresh_from_db()
        self.assertEqual(saldo.dias_usados, Decimal('0'))
        self.assertEqual(SolicitudLicencia.objects.get(pk=solicitud.pk).estado, 'CANCELADA')
        self.assertEqual(self.empleado.historial.count(), 2)

    def test_no_se_puede_aprobar_una_solicitud_rechazada(self):
        solicitud = self.crear_solicitud()
        solicitud.estado = SolicitudLicencia.Estado.RECHAZADA
        solicitud.save(update_fields=['estado'])

        with self.assertRaises(ValidationError):
            aprobar_solicitud(solicitud.pk, self.user)

    def test_no_se_puede_aprobar_una_solicitud_cancelada(self):
        solicitud = self.crear_solicitud()
        solicitud.estado = SolicitudLicencia.Estado.CANCELADA
        solicitud.save(update_fields=['estado'])

        with self.assertRaises(ValidationError):
            aprobar_solicitud(solicitud.pk, self.user)

    def test_saldo_insuficiente_no_cambia_estado_ni_registra_historial(self):
        solicitud = self.crear_solicitud()
        saldo = SaldoVacaciones.objects.create(
            empleado=self.empleado,
            anio=2026,
            dias_correspondientes=Decimal('2'),
            dias_usados=Decimal('0'),
        )

        with self.assertRaises(ValidationError):
            aprobar_solicitud(solicitud.pk, self.user)

        solicitud.refresh_from_db()
        saldo.refresh_from_db()
        self.assertEqual(solicitud.estado, SolicitudLicencia.Estado.PENDIENTE)
        self.assertEqual(saldo.dias_usados, Decimal('0'))
        self.assertFalse(self.empleado.historial.exists())

    def test_antiguedad_define_derecho_vacacional(self):
        casos = [
            (date(2022, 1, 1), 2026, Decimal('14')),
            (date(2021, 1, 1), 2026, Decimal('21')),
            (date(2016, 1, 1), 2026, Decimal('28')),
            (date(2006, 1, 1), 2026, Decimal('35')),
        ]
        for ingreso, anio, esperado in casos:
            self.empleado.fecha_ingreso = ingreso
            self.assertEqual(dias_vacaciones_por_antiguedad(self.empleado, anio), esperado)
