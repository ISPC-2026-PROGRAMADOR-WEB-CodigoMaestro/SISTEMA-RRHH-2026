from datetime import date
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.empleados.models import Empleado

from .models import AsistenciaCapacitacion, Curso, Inscripcion
from .services import emitir_certificado


class CapacitacionesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='test-dev3-capacitaciones', password='test-password',
        )
        self.empleado = Empleado.objects.create(
            legajo='CAP-100',
            numero_documento='CAP-100',
            apellido='Fernández',
            nombre='Laura',
            fecha_ingreso=date(2023, 1, 1),
        )
        self.curso = Curso.objects.create(
            nombre='Seguridad de la información',
            fecha_inicio=date(2026, 10, 1),
            fecha_fin=date(2026, 10, 2),
            horas=Decimal('4'),
            sesiones=2,
            asistencia_minima=Decimal('80'),
        )
        self.inscripcion = Inscripcion.objects.create(
            curso=self.curso,
            empleado=self.empleado,
        )

    def registrar_asistencia(self, presente=True):
        for fecha in (date(2026, 10, 1), date(2026, 10, 2)):
            AsistenciaCapacitacion.objects.create(
                inscripcion=self.inscripcion,
                fecha=fecha,
                presente=presente,
                registrada_por=self.user,
            )

    def test_no_emite_certificado_sin_asistencia_suficiente(self):
        self.registrar_asistencia(presente=False)

        with self.assertRaises(ValidationError):
            emitir_certificado(
                self.inscripcion.pk,
                SimpleUploadedFile('certificado.pdf', b'pdf'),
                self.user,
            )

    def test_certificado_se_agrega_al_legajo_y_registra_historial(self):
        self.registrar_asistencia()
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                certificado = emitir_certificado(
                    self.inscripcion.pk,
                    SimpleUploadedFile('certificado.pdf', b'contenido pdf'),
                    self.user,
                )

        self.assertEqual(certificado.documento_legajo.empleado, self.empleado)
        self.assertEqual(
            certificado.documento_legajo.categoria.nombre,
            'Certificados de capacitación',
        )
        self.assertEqual(self.empleado.historial.filter(referencia_app='capacitaciones').count(), 1)
        self.assertEqual(
            Inscripcion.objects.get(pk=self.inscripcion.pk).estado,
            Inscripcion.Estado.COMPLETADO,
        )
