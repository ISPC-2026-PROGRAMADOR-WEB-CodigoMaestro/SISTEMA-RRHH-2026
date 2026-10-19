"""Serializers de empleados, legajo digital e historial laboral."""
from rest_framework import serializers

from .models import CategoriaDocumento, DocumentoLegajo, Empleado, HistorialLaboral


class EmpleadoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    unidad_nombre = serializers.CharField(source='unidad.nombre', read_only=True)

    class Meta:
        model = Empleado
        fields = [
            'id', 'legajo', 'tipo_documento', 'numero_documento', 'cuil',
            'apellido', 'nombre', 'nombre_completo', 'fecha_nacimiento',
            'genero', 'nacionalidad', 'estado_civil',
            'email', 'telefono', 'telefono_alternativo', 'domicilio',
            'localidad', 'provincia', 'codigo_postal',
            'fecha_ingreso', 'fecha_egreso', 'estado', 'unidad', 'unidad_nombre',
            'usuario', 'foto', 'observaciones',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class CategoriaDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaDocumento
        fields = [
            'id', 'nombre', 'descripcion', 'requiere_vencimiento',
            'dias_alerta_previa', 'sensible', 'activa',
        ]


class DocumentoLegajoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    esta_vencido = serializers.BooleanField(read_only=True)

    class Meta:
        model = DocumentoLegajo
        fields = [
            'id', 'empleado', 'empleado_nombre', 'categoria', 'categoria_nombre',
            'titulo', 'descripcion', 'archivo', 'fecha_emision',
            'fecha_presentacion', 'fecha_vencimiento', 'cargado_por',
            'fecha_carga', 'activo', 'esta_vencido',
        ]
        read_only_fields = ['fecha_carga', 'cargado_por']


class HistorialLaboralSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.CharField(source='empleado.nombre_completo', read_only=True)
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_movimiento_display', read_only=True)

    class Meta:
        model = HistorialLaboral
        fields = [
            'id', 'empleado', 'empleado_nombre', 'fecha', 'tipo_movimiento',
            'tipo_display', 'descripcion', 'observaciones', 'usuario',
            'usuario_username', 'referencia_app', 'referencia_id', 'fecha_registro',
        ]
        read_only_fields = ['fecha_registro']
