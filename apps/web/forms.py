"""Formularios (ModelForms) con estilo Bootstrap para el dashboard."""
from django import forms

from apps.asistencia.models import RegistroAsistencia
from apps.empleados.models import DocumentoLegajo, Empleado
from apps.evaluaciones.models import EvaluacionDesempeno
from apps.incidencias.models import ComentarioIncidencia, Incidencia
from apps.licencias.models import SolicitudLicencia
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
            "estado", "unidad", "observaciones",
        ]
        widgets = {
            "fecha_nacimiento": DateInput(),
            "fecha_ingreso": DateInput(),
            "observaciones": forms.Textarea(attrs={"rows": 2}),
        }


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
        fields = ["empleado", "tipo_licencia", "fecha_inicio", "fecha_fin", "dias_solicitados", "motivo"]
        widgets = {
            "fecha_inicio": DateInput(),
            "fecha_fin": DateInput(),
            "motivo": forms.Textarea(attrs={"rows": 2}),
        }


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
        fields = ["empleado", "fecha_hecho", "tipo", "descripcion", "medida_adoptada", "dias_suspension", "estado"]
        widgets = {
            "fecha_hecho": DateInput(),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
            "medida_adoptada": forms.Textarea(attrs={"rows": 2}),
        }


class EvaluacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = EvaluacionDesempeno
        fields = ["empleado", "periodo", "fecha_evaluacion", "estado", "calificacion_general", "fortalezas", "aspectos_mejorar"]
        widgets = {
            "fecha_evaluacion": DateInput(),
            "fortalezas": forms.Textarea(attrs={"rows": 2}),
            "aspectos_mejorar": forms.Textarea(attrs={"rows": 2}),
        }
