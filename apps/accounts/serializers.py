"""Serializers de cuentas, perfiles, grupos y contraseña."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

from .models import PerfilUsuario

User = get_user_model()


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = [
            'id', 'rol', 'rol_display', 'telefono',
            'debe_cambiar_password', 'activo',
        ]
        read_only_fields = ['id']


class GrupoSerializer(serializers.ModelSerializer):
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ['id', 'name', 'permisos']

    def get_permisos(self, obj) -> list:
        return [
            f'{p.content_type.app_label}.{p.codename}'
            for p in obj.permissions.all()
        ]


class UserSerializer(serializers.ModelSerializer):
    perfil = PerfilUsuarioSerializer(read_only=True)
    grupos = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_staff', 'is_superuser', 'last_login',
            'perfil', 'grupos',
        ]
        read_only_fields = ['id', 'last_login', 'is_superuser']

    def get_grupos(self, obj) -> list:
        return [g.name for g in obj.groups.all()]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    rol = serializers.ChoiceField(
        choices=PerfilUsuario.RolPredeterminado.choices,
        default=PerfilUsuario.RolPredeterminado.ADMINISTRATIVO,
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'password', 'is_active', 'rol',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        rol = validated_data.pop('rol', PerfilUsuario.RolPredeterminado.ADMINISTRATIVO)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        PerfilUsuario.objects.create(usuario=user, rol=rol)
        asignar_grupo_por_rol(user, rol)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        rol = validated_data.pop('rol', None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        if password:
            instance.set_password(password)
        instance.save()
        if rol:
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=instance)
            perfil.rol = rol
            perfil.save()
            instance.groups.clear()
            asignar_grupo_por_rol(instance, rol)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=8)
    password_confirmacion = serializers.CharField(write_only=True)

    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def validate(self, attrs):
        if attrs['password_nuevo'] != attrs['password_confirmacion']:
            raise serializers.ValidationError(
                {'password_confirmacion': 'Las contraseñas nuevas no coinciden.'}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['password_nuevo'])
        user.save()
        perfil = getattr(user, 'perfil', None)
        if perfil is not None:
            perfil.debe_cambiar_password = False
            perfil.save(update_fields=['debe_cambiar_password'])
        return user


MAPA_ROL_GRUPO = {
    'GERENTE': 'Gerente General',
    'ADMINISTRATIVO': 'Administrativo de Recursos Humanos',
    'LECTURA': 'Solo lectura',
}


def asignar_grupo_por_rol(user, rol):
    """Asigna el grupo de Django correspondiente al rol indicado."""
    nombre = MAPA_ROL_GRUPO.get(rol)
    if not nombre:
        return
    grupo, _ = Group.objects.get_or_create(name=nombre)
    user.groups.add(grupo)
