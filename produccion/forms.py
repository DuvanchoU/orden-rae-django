from django import forms
from .models import Produccion

class ProduccionForm(forms.ModelForm):
    # Campo de estado con opciones predefinidas
    estado_produccion = forms.ChoiceField(
        choices=[
            ('', 'Seleccione el estado'),
            ('PENDIENTE', 'PENDIENTE'),
            ('EN PROCESO', 'EN PROCESO'),
            ('TERMINADA', 'TERMINADA'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Produccion
        fields = ['producto', 'cantidad_producida', 'fecha_inicio', 'fecha_fin', 
                  'estado_produccion', 'proveedor', 'observaciones']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cantidad_producida': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones adicionales (opcional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el texto de los selects
        self.fields['producto'].empty_label = "Seleccione un producto"
        self.fields['proveedor'].empty_label = "Seleccione un proveedor"