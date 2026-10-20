"""Formularios (ModelForms) con estilo Bootstrap para el dashboard."""
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.asistencia.models import RegistroAsistencia
from apps.capacitaciones.models import Curso
from apps.empleados.models import DocumentoLegajo, Empleado
from apps.evaluaciones.models import EvaluacionDesempeno
from apps.incidencias.models import ComentarioIncidencia, Incidencia
from apps.licencias.models import SolicitudLicencia, TipoLicencia
from apps.licencias.services import validar_solicitud
from apps.organizacion.models import UnidadOrganizacional
from apps.puestos.models import Designacion, Puesto
from apps.sanciones.models import Sancion


class DateInput(forms.DateInput):
    input_type = "date"


class BootstrapMixin:
    """Aplica clases de Bootstrap a todos los widgets del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + css).strip()


class EmpleadoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Empleado
        fields = [
            "legajo", "tipo_documento", "numero_documento", "cuil",
            "apellido", "nombre", "fecha_nacimiento", "genero",
            "email", "telefono", "domicilio", "fecha_ingreso",
            "estado", "unidad", "usuario", "observaciones",
        ]
        labels = {"usuario": "Cuenta de acceso (opcional)"}
        widgets = {
            "fecha_nacimiento": DateInput(),
            "fecha_ingreso": DateInput(),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = get_user_model().objects.filter(
            is_active=True,
            empleado__isnull=True,
        )
        if self.instance.pk and self.instance.usuario_id:
            usuarios = get_user_model().objects.filter(
                Q(is_active=True, empleado__isnull=True)
                | Q(pk=self.instance.usuario_id)
            )
        self.fields["usuario"].queryset = usuarios.order_by("username")


class UnidadForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = UnidadOrganizacional
        fields = ["codigo", "nombre", "tipo", "parent", "orden", "activa", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


class PuestoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Puesto
        fields = [
            "codigo", "denominacion", "unidad", "puesto_superior",
            "nivel_autoridad", "cantidad_prevista", "objetivo_general",
            "activo",
        ]
        widgets = {"objetivo_general": forms.Textarea(attrs={"rows": 2})}


class DesignacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Designacion
        fields = [
            "empleado", "puesto", "fecha_inicio", "modalidad_contractual",
            "jornada", "superior_jerarquico", "activa", "observaciones",
        ]
        widgets = {"fecha_inicio": DateInput()}


class DocumentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = DocumentoLegajo
        fields = [
            "empleado", "categoria", "titulo", "archivo",
            "fecha_emision", "fecha_vencimiento", "descripcion",
        ]
        widgets = {
            "fecha_emision": DateInput(),
            "fecha_vencimiento": DateInput(),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }


class AsistenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = RegistroAsistencia
        fields = ["empleado", "fecha", "hora_ingreso", "hora_egreso", "tipo", "justificado", "observaciones"]
        widgets = {
            "fecha": DateInput(),
            "hora_ingreso": forms.TimeInput(attrs={"type": "time"}),
            "hora_egreso": forms.TimeInput(attrs={"type": "time"}),
        }


class SolicitudLicenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SolicitudLicencia
        fields = ["empleado", "tipo_licencia", "fecha_inicio", "fecha_fin", "motivo"]
        widgets = {
            "fecha_inicio": DateInput(),
            "fecha_fin": DateInput(),
            "motivo": forms.Textarea(attrs={"rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        tipo = cleaned_data.get('tipo_licencia')
        inicio = cleaned_data.get('fecha_inicio')
        fin = cleaned_data.get('fecha_fin')
        if empleado and tipo and inicio and fin:
            if self.instance.pk and self.instance.estado not in (
                SolicitudLicencia.Estado.PENDIENTE,
                SolicitudLicencia.Estado.BORRADOR,
            ):
                raise forms.ValidationError(
                    'Solo se pueden editar solicitudes pendientes o en borrador.'
                )
            try:
                cleaned_data['dias_solicitados'] = validar_solicitud(
                    empleado,
                    tipo,
                    inicio,
                    fin,
                    excluir_id=self.instance.pk if self.instance.pk else None,
                )
            except ValidationError as exc:
                if hasattr(exc, 'message_dict'):
                    for field, errors in exc.message_dict.items():
                        for error in errors:
                            self.add_error(field if field in self.fields else None, error)
                else:
                    self.add_error(None, exc.messages)
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.dias_solicitados = self.cleaned_data['dias_solicitados']
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class LicenciaAutogestionForm(BootstrapMixin, forms.Form):
    tipo_licencia = forms.ModelChoiceField(
        label='Tipo de licencia',
        queryset=TipoLicencia.objects.filter(activo=True),
    )
    fecha_inicio = forms.DateField(label='Desde', widget=DateInput())
    fecha_fin = forms.DateField(label='Hasta', widget=DateInput())
    motivo = forms.CharField(
        label='Motivo',
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, empleado, **kwargs):
        self.empleado = empleado
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_licencia')
        inicio = cleaned_data.get('fecha_inicio')
        fin = cleaned_data.get('fecha_fin')
        if tipo and inicio and fin:
            try:
                cleaned_data['dias_solicitados'] = validar_solicitud(
                    self.empleado, tipo, inicio, fin,
                )
            except ValidationError as exc:
                if hasattr(exc, 'message_dict'):
                    for field, errors in exc.message_dict.items():
                        for error in errors:
                            self.add_error(field if field in self.fields else None, error)
                else:
                    self.add_error(None, exc.messages)
        return cleaned_data


class IncidenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = ["empleado", "unidad", "categoria", "titulo", "descripcion", "prioridad", "fecha_estimada_resolucion"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
            "fecha_estimada_resolucion": DateInput(),
        }


class SancionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Sancion
        fields = ["empleado", "fecha_hecho", "tipo", "descripcion", "medida_adoptada", "dias_suspension", "normativa_incumplida"]
        widgets = {
            "fecha_hecho": DateInput(),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
            "medida_adoptada": forms.Textarea(attrs={"rows": 2}),
        }


class EvaluacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = EvaluacionDesempeno
        fields = ["empleado", "periodo", "fecha_evaluacion", "fortalezas", "aspectos_mejorar"]
        widgets = {
            "fecha_evaluacion": DateInput(),
            "fortalezas": forms.Textarea(attrs={"rows": 2}),
            "aspectos_mejorar": forms.Textarea(attrs={"rows": 2}),
        }


class CursoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Curso
        fields = [
            "nombre", "descripcion", "instructor", "fecha_inicio", "fecha_fin",
            "horas", "sesiones", "asistencia_minima", "cupo", "activo",
        ]
        widgets = {
            "fecha_inicio": DateInput(),
            "fecha_fin": DateInput(),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }
