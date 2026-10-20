"""Pruebas funcionales de la API (Fase 2)."""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class ApiFlujoTest(APITestCase):
    """Smoke test del flujo principal: login JWT + modulos."""

    def setUp(self):
        self.user = User.objects.create_superuser('tester', 't@t.com', 'test12345')
        resp = self.client.post(
            '/api/auth/login/',
            {'username': 'tester', 'password': 'test12345'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + resp.data['access'])

    def test_perfil_actual(self):
        r = self.client.get('/api/accounts/me/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['username'], 'tester')

    def test_flujo_completo(self):
        # 1) Unidad organizacional
        r = self.client.post(
            '/api/organizacion/unidades/',
            {'codigo': 'GG', 'nombre': 'Gerencia General', 'tipo': 'GERENCIA'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        unidad_id = r.data['id']

        # 2) Empleado
        r = self.client.post(
            '/api/empleados/empleados/',
            {
                'legajo': '0001', 'tipo_documento': 'DNI',
                'numero_documento': '12345678', 'apellido': 'Perez',
                'nombre': 'Juan', 'fecha_ingreso': '2024-01-15',
                'unidad': unidad_id,
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        empleado_id = r.data['id']

        # 3) Puesto
        r = self.client.post(
            '/api/puestos/puestos/',
            {'codigo': 'P-001', 'denominacion': 'Analista', 'unidad': unidad_id,
             'cantidad_prevista': 2},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        puesto_id = r.data['id']
        self.assertEqual(r.data['cantidad_vacantes'], 2)

        # 4) Designacion
        r = self.client.post(
            '/api/puestos/designaciones/',
            {'empleado': empleado_id, 'puesto': puesto_id, 'fecha_inicio': '2024-01-15'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        # 5) Organigrama
        r = self.client.get('/api/organizacion/unidades/organigrama/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

        # 6) Planta funcional
        r = self.client.get('/api/puestos/puestos/planta_funcional/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(any(p['ocupados'] == 1 for p in r.data))

        # 7) Registro de asistencia
        r = self.client.post(
            '/api/asistencia/registros/',
            {'empleado': empleado_id, 'fecha': '2024-01-15', 'tipo': 'PRESENTE'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)

        # 8) Incidencia (numero autogenerado)
        r = self.client.post(
            '/api/incidencias/incidencias/',
            {'empleado': empleado_id, 'categoria': 'ASISTENCIA',
             'titulo': 'Falta injustificada', 'descripcion': 'Prueba',
             'prioridad': 'ALTA'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertTrue(r.data['numero'].startswith('INC-'))

        # 9) Auditoria registro movimientos
        r = self.client.get('/api/auditoria/registros/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(r.data['count'], 4)

    def test_login_invalido(self):
        resp = self.client.post(
            '/api/auth/login/',
            {'username': 'tester', 'password': 'mala'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
