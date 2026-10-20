from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import PerfilUsuario
from apps.empleados.models import Empleado

from .models import Sancion
from .services import transicionar_sancion


class FlujoSancionesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.gerente = User.objects.create_superuser(
            username='test-dev3-gerente', password='test-password',
        )
        self.admin = User.objects.create_user(
            username='test-dev3-admin', password='test-password',
        )
        PerfilUsuario.objects.create(
            usuario=self.admin,
            rol=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
        )
        self.empleado_user = User.objects.create_user(
            username='test-dev3-empleado', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='SAN-100',
            numero_documento='SAN-100',
            apellido='Díaz',
            nombre='Julia',
            fecha_ingreso=date(2020, 1, 1),
            usuario=self.empleado_user,
        )
        self.sancion = Sancion.objects.create(
            empleado=self.empleado,
            fecha_hecho=date(2026, 10, 1),
            tipo=Sancion.Tipo.APERCIBIMIENTO,
            descripcion='Incumplimiento de procedimiento.',
            medida_adoptada='Apercibimiento formal.',
        )

    def test_transicion_propuesta_notificada_aplicada_registra_historial(self):
        transicionar_sancion(self.sancion.pk, 'notificar', self.admin)
        sancion = transicionar_sancion(self.sancion.pk, 'aplicar', self.gerente)

        self.assertEqual(sancion.estado, Sancion.Estado.APLICADA)
        self.assertIsNotNone(sancion.fecha_notificacion)
        self.assertIsNotNone(sancion.fecha_aplicacion)
        self.assertEqual(self.empleado.historial.filter(referencia_app='sanciones').count(), 2)

    def test_solo_el_empleado_vinculado_puede_apelar(self):
        transicionar_sancion(self.sancion.pk, 'notificar', self.admin)

        with self.assertRaises(PermissionDenied):
            transicionar_sancion(self.sancion.pk, 'apelar', self.admin)

        sancion = transicionar_sancion(
            self.sancion.pk,
            'apelar',
            self.empleado_user,
            'Presento mi descargo.',
        )
        self.assertEqual(sancion.estado, Sancion.Estado.APELADA)
        self.assertEqual(sancion.descargo_trabajador, 'Presento mi descargo.')

    def test_no_se_puede_aplicar_una_sancion_sin_notificar(self):
        with self.assertRaises(ValidationError):
            transicionar_sancion(self.sancion.pk, 'aplicar', self.gerente)

    def test_suspension_requiere_cantidad_de_dias(self):
        self.sancion.tipo = Sancion.Tipo.SUSPENSION

        with self.assertRaises(ValidationError):
            self.sancion.full_clean()

    def test_api_permita_apelacion_del_empleado_vinculado(self):
        transicionar_sancion(self.sancion.pk, 'notificar', self.admin)
        client = APIClient()
        client.force_authenticate(self.empleado_user)

        response = client.post(
            f'/api/sanciones/sanciones/{self.sancion.pk}/apelar/',
            {'observacion': 'Apelo esta medida.'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['estado'], Sancion.Estado.APELADA)

# Create your tests here.
