from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from apps.empleados.models import Empleado

from .models import CriterioEvaluacion, DetalleEvaluacion, EvaluacionDesempeno, PeriodoEvaluacion
from .services import (
    calcular_puntaje_ponderado,
    cambiar_estado_evaluacion,
    comparar_con_periodo_anterior,
)


class EvaluacionesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='test-dev3-evaluacion', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='EVA-100',
            numero_documento='EVA-100',
            apellido='Martínez',
            nombre='Eva',
            fecha_ingreso=date(2020, 1, 1),
        )
        self.criterio_a = CriterioEvaluacion.objects.create(
            nombre='Calidad', peso=Decimal('2'),
        )
        self.criterio_b = CriterioEvaluacion.objects.create(
            nombre='Colaboración', peso=Decimal('1'),
        )
        self.periodo_anterior = PeriodoEvaluacion.objects.create(
            nombre='2025',
            fecha_inicio=date(2025, 1, 1),
            fecha_fin=date(2025, 12, 31),
        )
        self.periodo_actual = PeriodoEvaluacion.objects.create(
            nombre='2026',
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
        )

    def crear_evaluacion(self, periodo, estado=EvaluacionDesempeno.Estado.EN_CURSO):
        return EvaluacionDesempeno.objects.create(
            empleado=self.empleado,
            periodo=periodo,
            evaluador=self.user,
            fecha_evaluacion=periodo.fecha_fin,
            estado=estado,
        )

    def test_puntaje_ponderado_usa_pesos(self):
        puntaje = calcular_puntaje_ponderado([
            {'criterio': self.criterio_a, 'calificacion': Decimal('80')},
            {'criterio': self.criterio_b, 'calificacion': Decimal('100')},
        ])

        self.assertEqual(puntaje, Decimal('86.67'))

    def test_finalizar_calcula_puntaje_y_registra_historial(self):
        evaluacion = self.crear_evaluacion(self.periodo_actual)
        DetalleEvaluacion.objects.create(
            evaluacion=evaluacion, criterio=self.criterio_a, calificacion=90,
        )

        finalizada = cambiar_estado_evaluacion(evaluacion.pk, 'finalizar', self.user)

        self.assertEqual(finalizada.estado, EvaluacionDesempeno.Estado.FINALIZADA)
        self.assertEqual(finalizada.calificacion_general, Decimal('90.00'))
        self.assertEqual(self.empleado.historial.filter(referencia_app='evaluaciones').count(), 1)

    def test_no_se_finaliza_sin_criterios_calificados(self):
        evaluacion = self.crear_evaluacion(self.periodo_actual)

        with self.assertRaises(ValidationError):
            cambiar_estado_evaluacion(evaluacion.pk, 'finalizar', self.user)

    def test_compara_con_evaluacion_finalizada_anterior(self):
        anterior = self.crear_evaluacion(
            self.periodo_anterior,
            EvaluacionDesempeno.Estado.FINALIZADA,
        )
        anterior.calificacion_general = Decimal('70')
        anterior.save(update_fields=['calificacion_general'])
        actual = self.crear_evaluacion(
            self.periodo_actual,
            EvaluacionDesempeno.Estado.FINALIZADA,
        )
        actual.calificacion_general = Decimal('85')
        actual.save(update_fields=['calificacion_general'])

        comparacion = comparar_con_periodo_anterior(actual)

        self.assertEqual(comparacion['puntaje_anterior'], Decimal('70'))
        self.assertEqual(comparacion['variacion'], Decimal('15'))

    def test_api_calcula_puntaje_ponderado_al_crear(self):
        client = APIClient()
        client.force_authenticate(self.user)

        response = client.post('/api/evaluaciones/evaluaciones/', {
            'empleado': self.empleado.pk,
            'periodo': self.periodo_actual.pk,
            'fecha_evaluacion': '2026-06-30',
            'detalles': [
                {'criterio': self.criterio_a.pk, 'calificacion': '80'},
                {'criterio': self.criterio_b.pk, 'calificacion': '100'},
            ],
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['calificacion_general'], '86.67')

# Create your tests here.
