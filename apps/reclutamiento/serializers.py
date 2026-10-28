
"""Serializers de vacantes, postulantes, postulaciones y entrevistas."""
from rest_framework import serializers

from .models import Entrevista, Postulacion, Postulante, Vacante


class VacanteSerializer(serializers.ModelSerializer):
    puesto_denominacion = serializers.CharField(source='puesto.denominacion', read_only=True)

    class Meta:
        model = Vacante
        fields = [
            'id', 'puesto', 'puesto_denominacion', 'titulo',
            'descripcion', 'requisitos', 'cantidad_vacantes',
            'fecha_publicacion', 'fecha_cierre', 'estado',
            'fecha_creacion', 'fecha_actualizacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']


class PostulanteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Postulante
        fields = [
            'id', 'nombre', 'apellido', 'numero_documento',
            'email', 'telefono', 'formacion', 'experiencia',
            'curriculum', 'observaciones', 'fecha_registro',
        ]
        read_only_fields = ['fecha_registro']


class PostulacionSerializer(serializers.ModelSerializer):
    postulante_nombre = serializers.CharField(source='postulante.__str__', read_only=True)
    vacante_titulo = serializers.CharField(source='vacante.titulo', read_only=True)

    class Meta:
        model = Postulacion
        fields = [
            'id', 'postulante', 'postulante_nombre',
            'vacante', 'vacante_titulo', 'fecha_postulacion',
            'estado', 'observaciones',
        ]
        read_only_fields = ['fecha_postulacion']


class EntrevistaSerializer(serializers.ModelSerializer):
    postulante_nombre = serializers.CharField(source='postulacion.postulante.__str__', read_only=True)

    class Meta:
        model = Entrevista
        fields = [
            'id', 'postulacion', 'postulante_nombre',
            'fecha', 'entrevistador', 'observaciones',
            'resultado', 'fecha_creacion',
        ]
        read_only_fields = ['fecha_creacion']
