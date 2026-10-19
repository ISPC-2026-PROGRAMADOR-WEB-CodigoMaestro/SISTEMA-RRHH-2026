"""Formulario para crear/editar usuarios desde el dashboard."""
from django import forms
from django.contrib.auth import get_user_model

from .forms import BootstrapMixin

User = get_user_model()

ROLES = [
    ('GERENTE', 'Gerente General'),
    ('ADMINISTRATIVO', 'Administrativo de Recursos Humanos'),
    ('LECTURA', 'Solo lectura'),
]


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        required=False,
        min_length=8,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Obligatoria al crear. En edición, dejala vacía para no cambiarla.',
    )
    rol = forms.ChoiceField(label='Rol', choices=ROLES)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo electrónico',
            'is_active': 'Activo',
        }
