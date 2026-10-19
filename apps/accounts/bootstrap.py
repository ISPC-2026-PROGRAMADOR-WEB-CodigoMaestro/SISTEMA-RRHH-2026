"""
Arranque automático del sistema.

Al ejecutar `migrate` crea (de forma idempotente):
- Grupos/roles de RRHH.
- Usuarios hardcodeados (superadmin + multiusuario para demo/feria).
- Datos base: categorías de documento, tipos de licencia y criterios de evaluación.

Usa get_or_create, por lo que puede ejecutarse muchas veces sin duplicar datos.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

User = get_user_model()

USUARIOS_HARDCODEADOS = [
    {
        'username': 'admin',
        'password': 'admin123',
        'email': 'admin@rrhh.local',
        'first_name': 'Administrador',
        'last_name': 'General',
        'rol': 'GERENTE',
        'grupo': 'Gerente General',
        'is_superuser': True,
        'is_staff': True,
    },
    {
        'username': 'rrhh',
        'password': 'rrhh1234',
        'email': 'rrhh@rrhh.local',
        'first_name': 'Ramiro',
        'last_name': 'Rodriguez',
        'rol': 'ADMINISTRATIVO',
        'grupo': 'Administrativo de Recursos Humanos',
        'is_superuser': False,
        'is_staff': False,
    },
    {
        'username': 'consulta',
        'password': 'consulta1234',
        'email': 'consulta@rrhh.local',
        'first_name': 'Carla',
        'last_name': 'Fernandez',
        'rol': 'LECTURA',
        'grupo': 'Solo lectura',
        'is_superuser': False,
        'is_staff': False,
    },
]


def _crear_grupos():
    definicion = {
        'Gerente General': Permission.objects.all(),
        'Administrativo de Recursos Humanos': Permission.objects.exclude(
            content_type__app_label__in=['auth', 'admin', 'sessions', 'contenttypes']
        ).exclude(codename__startswith='delete_'),
        'Solo lectura': Permission.objects.filter(codename__startswith='view_'),
    }
    for nombre, permisos in definicion.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        grupo.permissions.set(permisos)


def _crear_usuarios():
    from .models import PerfilUsuario

    for datos in USUARIOS_HARDCODEADOS:
        username = datos['username']
        defaults = {
            'email': datos['email'],
            'first_name': datos['first_name'],
            'last_name': datos['last_name'],
        }
        user, creado = User.objects.get_or_create(username=username, defaults=defaults)
        if creado:
            user.set_password(datos['password'])
            user.is_superuser = datos['is_superuser']
            user.is_staff = datos['is_staff']
            user.save()

        perfil, _ = PerfilUsuario.objects.get_or_create(
            usuario=user, defaults={'rol': datos['rol']}
        )
        if perfil.rol != datos['rol']:
            perfil.rol = datos['rol']
            perfil.save(update_fields=['rol'])

        try:
            grupo = Group.objects.get(name=datos['grupo'])
            user.groups.add(grupo)
        except Group.DoesNotExist:
            pass


def _seed_categorias():
    from apps.empleados.models import CategoriaDocumento

    cats = [
        ('Contrato', True, 30, True),
        ('DNI / Identificacion', False, 0, True),
        ('CUIL', False, 0, True),
        ('Titulo / Certificacion', False, 0, False),
        ('Matricula profesional', True, 60, False),
        ('Examen medico', True, 30, True),
        ('Constancia', False, 0, False),
        ('Recibo de sueldo', False, 0, True),
        ('Notificacion', False, 0, False),
        ('Licencia / Certificado', True, 15, True),
        ('Sancion', False, 0, True),
        ('Otro', False, 0, False),
    ]
    for nombre, vence, dias, sensible in cats:
        CategoriaDocumento.objects.get_or_create(
            nombre=nombre,
            defaults={
                'requiere_vencimiento': vence,
                'dias_alerta_previa': dias,
                'sensible': sensible,
            },
        )


def _seed_tipos_licencia():
    from apps.licencias.models import TipoLicencia

    tipos = [
        ('VAC', 'Vacaciones', None, True, True),
        ('ENF', 'Licencia por enfermedad', None, True, False),
        ('MAT', 'Licencia por maternidad', 90, True, False),
        ('PAT', 'Licencia por paternidad', 15, True, False),
        ('EST', 'Licencia por estudio', 10, True, False),
        ('ACC', 'Licencia por accidente', None, True, False),
        ('PAR', 'Asuntos particulares', 5, True, False),
        ('DOL', 'Duelo', 3, True, False),
    ]
    for codigo, nombre, dias, aprueba, descuenta in tipos:
        TipoLicencia.objects.get_or_create(
            codigo=codigo,
            defaults={
                'nombre': nombre,
                'dias_maximos': dias,
                'requiere_aprobacion': aprueba,
                'descuenta_vacaciones': descuenta,
            },
        )


def _seed_criterios():
    from apps.evaluaciones.models import CriterioEvaluacion

    criterios = [
        ('Cumplimiento de objetivos', 1.5, 1),
        ('Calidad del trabajo', 1.5, 2),
        ('Productividad', 1.2, 3),
        ('Responsabilidad', 1.2, 4),
        ('Trabajo en equipo', 1.0, 5),
        ('Liderazgo', 1.0, 6),
        ('Competencias tecnicas', 1.3, 7),
        ('Conducta laboral', 1.0, 8),
    ]
    for nombre, peso, orden in criterios:
        CriterioEvaluacion.objects.get_or_create(
            nombre=nombre, defaults={'peso': peso, 'orden': orden}
        )


def ejecutar_bootstrap():
    """Ejecuta toda la carga inicial. Idempotente."""
    _crear_grupos()
    _crear_usuarios()
    _seed_categorias()
    _seed_tipos_licencia()
    _seed_criterios()

