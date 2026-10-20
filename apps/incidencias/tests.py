from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empleados.models import Empleado

from .models import Incidencia
from .services import cambiar_estado_incidencia


class FlujoIncidenciasTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='test-dev3-incidencia', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='INC-100',
            numero_documento='INC-100',
            apellido='Suárez',
            nombre='Pablo',
            fecha_ingreso=date(2021, 1, 1),
        )
        self.incidencia = Incidencia.objects.create(
            empleado=self.empleado,
            categoria=Incidencia.Categoria.ASISTENCIA,
            titulo='Marcación faltante',
            descripcion='No aparece la marcación de ingreso.',
        )

    def test_cambio_a_cerrada_registra_fecha_de_resolucion(self):
        cambiar_estado_incidencia(self.incidencia.pk, Incidencia.Estado.EN_ANALISIS)
        resuelta = cambiar_estado_incidencia(self.incidencia.pk, Incidencia.Estado.RESUELTA)
        cerrada = cambiar_estado_incidencia(self.incidencia.pk, Incidencia.Estado.CERRADA)

        self.assertIsNotNone(resuelta.fecha_resolucion)
        self.assertEqual(cerrada.estado, Incidencia.Estado.CERRADA)
        self.assertIsNotNone(cerrada.fecha_resolucion)

    def test_no_se_puede_cerrar_una_incidencia_abierta(self):
        with self.assertRaises(ValidationError):
            cambiar_estado_incidencia(self.incidencia.pk, Incidencia.Estado.CERRADA)

    def test_fecha_estimada_anterior_a_creacion_es_invalida(self):
        self.incidencia.fecha_estimada_resolucion = timezone.localdate() - timedelta(days=1)

        with self.assertRaises(ValidationError):
            self.incidencia.full_clean()

    def test_api_rechaza_salto_de_estado_invalido(self):
        client = APIClient()
        self.user.is_superuser = True
        self.user.save(update_fields=['is_superuser'])
        client.force_authenticate(self.user)

        response = client.post(
            f'/api/incidencias/incidencias/{self.incidencia.pk}/cambiar_estado/',
            {'estado': Incidencia.Estado.CERRADA},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.incidencia.refresh_from_db()
        self.assertEqual(self.incidencia.estado, Incidencia.Estado.ABIERTA)

# Create your tests here.
