from django import forms

from apps.empleados.models import Empleado

from .models import HorarioDiario


class HorarioDiarioForm(forms.ModelForm):
    alcance = forms.ChoiceField(
        label='Aplicación del horario',
        choices=[
            ('solo_fecha', 'Solo esta fecha'),
            ('predeterminado', 'Cambiar el horario predeterminado desde esta fecha'),
        ],
        widget=forms.RadioSelect,
        initial='solo_fecha',
    )

    class Meta:
        model = HorarioDiario
        fields = [
            'empleado',
            'fecha',
            'hora_entrada',
            'hora_salida',
            'es_franco',
            'observaciones',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora_entrada': forms.TimeInput(attrs={'type': 'time'}),
            'hora_salida': forms.TimeInput(attrs={'type': 'time'}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['empleado'].queryset = Empleado.objects.order_by(
            'apellido',
            'nombre',
        )
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = 'form-check-input'
            elif isinstance(field.widget, forms.RadioSelect):
                continue
            elif isinstance(field.widget, forms.Select):
                css_class = 'form-select'
            else:
                css_class = 'form-control'
            field.widget.attrs['class'] = css_class

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('es_franco'):
            cleaned_data['hora_entrada'] = None
            cleaned_data['hora_salida'] = None
            if cleaned_data.get('alcance') == 'predeterminado':
                self.add_error(
                    'alcance',
                    'Un día franco no puede convertirse en horario predeterminado.',
                )
        return cleaned_data

    def save(self, commit=True):
        horario = super().save(commit=False)
        if commit:
            horario.full_clean()
            horario.save()
            self.save_m2m()
        return horario
