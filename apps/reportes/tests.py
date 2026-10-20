"""Pruebas de la app reportes (Fase 6)."""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.empleados.models import Empleado

User = get_user_model()


class ReportesTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('rep', 'r@r.com', 'test12345')
        resp = self.client.post(
            '/api/auth/login/',
            {'username': 'rep', 'password': 'test12345'},
            format='json',
        )
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + resp.data['access'])
        Empleado.objects.create(
            legajo='0009', tipo_documento='DNI', numero_documento='99999999',
            apellido='Lopez', nombre='Ana', fecha_ingreso='2020-01-01',
        )

    def test_resumen(self):
        r = self.client.get('/api/reportes/resumen/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('empleados_activos', r.data)
        self.assertEqual(r.data['empleados_activos'], 1)

    def test_nomina_json(self):
        r = self.client.get('/api/reportes/nomina/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total'], 1)

    def test_nomina_excel(self):
        r = self.client.get('/api/reportes/nomina/?formato=excel')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', r['Content-Type'])

    def test_nomina_pdf(self):
        r = self.client.get('/api/reportes/nomina/?formato=pdf')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_promociones_potenciales(self):
        r = self.client.get('/api/reportes/promociones-potenciales/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total'], 1)

